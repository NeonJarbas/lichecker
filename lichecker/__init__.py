import subprocess

from lichecker.exception import NoDerivativesException, BadLicense, AmbiguousLicense, \
    UnidirectionalCodeFlow, SoftwareSpecific, UnknownLicense, InconsistentLicense


class DependencyChecker:
    cache = {}

    def __init__(self, pkg_name):
        self.pkg_name = pkg_name
        self._transient_dependencies = {}
        self._data = {}
        self._deps = []

    @property
    def license(self):
        if not self._data:
            self._data = self.get_package_data(self.pkg_name)
        return self._data.get("License")

    @property
    def version(self):
        if not self._data:
            self._data = self.get_package_data(self.pkg_name)
        return self._data.get("Version")

    @property
    def dependencies(self):
        if not self._deps:
            r = self.get_package_data(self.pkg_name).get('Requires')
            r = r.split(", ") if r else []
            self._deps = [dep for dep in r if dep and dep != self.pkg_name]
        return self._deps

    @property
    def transient_dependencies(self):
        all_deps = list(self._transient_dependencies.keys())
        new_deps = [k for k in self.dependencies if k not in all_deps]
        while new_deps:
            for dep in new_deps:
                self._transient_dependencies[dep] = self.get_direct_dependencies(dep)
            new_deps = []
            for p, deps in self._transient_dependencies.items():
                new_deps += [d for d in deps if d not in self._transient_dependencies]
            #   print("### ", p, deps)
        return self._transient_dependencies

    @staticmethod
    def get_package_data(pkg_name, cache=True):
        pkg_name = pkg_name.strip().replace("_", "-")  # pip normalizes this internally, removes duplicate entries since packages can use either
        if cache and DependencyChecker.cache.get(pkg_name):
            return DependencyChecker.cache[pkg_name]
        try:
            out = subprocess.check_output(["pip", "show", pkg_name]).decode("utf-8")
            lines = (l.split(": ") for l in out.split("\n") if ": " in l)
            data = {k: v for k, v in lines if v}
            if cache and data:
                DependencyChecker.cache[pkg_name] = data
        except subprocess.CalledProcessError as e:
            print(e)
            return {}
        return data

    @staticmethod
    def get_license(pkg_name):
        return DependencyChecker.get_package_data(pkg_name).get("License")

    @staticmethod
    def get_direct_dependencies(pkg_name):
        # print("# parsing", pkg_name)
        r = DependencyChecker.get_package_data(pkg_name).get('Requires')
        return r.split(", ") if r else []

    @property
    def versions(self):
        return {p: self.get_package_data(p).get("Version")
                for p in self.transient_dependencies}

    @property
    def licenses(self):
        return {p: self.get_package_data(p).get("License") or "UNKNOWN"
                for p in self.transient_dependencies}


class LicenseChecker(DependencyChecker):
    ALIASES = {
        'BSD-0-Clause': "BSD0",
        'BSD-2-Clause': "BSD2",
        'BSD-3-Clause': "BSD3",
        'ASL 2.0': 'Apache-2.0',
        "Python Software Foundation License": "PSFL"
    }

    def __init__(self, pkg_name, license_overrides=None, whitelisted_packages=None,
                 allow_nonfree=False, allow_viral=False, allow_unknown=False,
                 allow_unlicense=False, allow_ambiguous=False):
        super().__init__(pkg_name)
        self._license_overrides = license_overrides or {}
        self._whitelist = whitelisted_packages or []
        self.allow_nonfree = allow_nonfree
        self.allow_viral = allow_viral
        self.allow_unknown = allow_unknown
        self.allow_unlicense = allow_unlicense
        self.allow_ambiguous = allow_ambiguous

    @staticmethod
    def normalize_license_name(li):
        li = li.strip()
        if li in LicenseChecker.ALIASES:
            return LicenseChecker.ALIASES[li]
        if li.lower().endswith(" license"):
            li = li[:-7].strip()
        if "apache" in li.lower():
            return 'Apache-2.0'
        if "ZPL" in li:
            return 'ZPL'
        return LicenseChecker.ALIASES.get(li) or li

    @property
    def licenses(self):
        return {p: self._license_overrides.get(p) or self.get_package_data(p).get("License")
                for p in self.transient_dependencies}

    def validate(self):
        valid = ["mit", 'apache-2.0', 'unlicense', 'mpl-2.0', 'isc', 'bsd3', 'bsd2', 'bsd', 'psfl', 'zpl']
        for pkg, li in self.licenses.items():
            if pkg in self._whitelist:
                print(f"{pkg} explicitly allowed, skipping license check")
                continue
            li = self.normalize_license_name(li)
            if "gpl" in li.lower() and not self.allow_viral:
                raise UnidirectionalCodeFlow(f"{pkg} is licensed under {li} which places restrictions in larger works")
            elif 'unlicense' in li.lower() and not self.allow_unlicense:
                raise InconsistentLicense("Unlicense is not global. It doesn't make sense in some jurisdictions.\n"
                                          "It's inconsistent. Some of the warranty terms cannot, logically, co-exist.\n"
                                          "The license is short, clearly expressing intent, at the cost of not carefully addressing common license, copy-right and warranty issues.")

            elif not self.allow_nonfree and not self.allow_unknown:
                if not li or li.lower() not in valid:
                    raise UnknownLicense(f"{pkg} license unknown, no permissions given")


if __name__ == "__main__":
    from pprint import pprint

    # these packages dont define license in setup.py
    # manually verified and injected
    license_overrides = {
        "kthread": "MIT",
        'yt-dlp': "Unlicense",
        'pyxdg': 'GPL-2.0',
        'ptyprocess': 'ISC license',
        'psutil': 'BSD3'
    }
    # explicitly allow these packages that would fail otherwise
    whitelist = [
        'idna',  # BSD-like
        "pyxdg"  # TODO Remove ASAP main offender found in ovos
    ]
    # validation flags
    allow_nonfree = False
    allow_viral = False
    allow_unknown = False
    allow_unlicense = True
    allow_ambiguous = False


    def test(pkg_name):
        licheck = LicenseChecker(pkg_name,
                                 license_overrides=license_overrides,
                                 whitelisted_packages=whitelist,
                                 allow_ambiguous=allow_ambiguous,
                                 allow_unlicense=allow_unlicense,
                                 allow_unknown=allow_unknown,
                                 allow_viral=allow_viral,
                                 allow_nonfree=allow_nonfree)
        print("Package", pkg_name)
        print("Version", licheck.version)
        print("License", licheck.license)

        print("Requirements")
        pprint(licheck.dependencies)

        print("Transient Requirements (dependencies of dependencies)")
        pprint(licheck.transient_dependencies)

        print("Package Versions")
        pprint(licheck.versions)

        print("Dependency Licenses")
        pprint(licheck.licenses)

        licheck.validate()


    # test("requests")
    test("ovos-workshop")
