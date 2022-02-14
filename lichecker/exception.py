
class UnknownLicense(Exception):
    """ Unknown License, no permissions given """


class UnidirectionalCodeFlow(Exception):
    """Viral Licenses prevent code flow from code into other works being under different even OSI compliant licenses"""
    # all GPLs


class PythonLinkingException(UnidirectionalCodeFlow):
    """The applicability of the LGPL's linking exception to interpreted languages like Python is unclear"""
    # LGPL


class NoDerivativesException(UnidirectionalCodeFlow):
    """ The License permits only contributions and anhancements to the original work but does not allow to use code in another work"""
    # EPL / CPL


class BadLicense(Exception):
    """ License contains unacceptable clauses """


class InconsistentLicense(BadLicense):
    """License contradicts itself, it is not consistent"""
    # unlicense - https://softwareengineering.stackexchange.com/questions/147111/what-is-wrong-with-the-unlicense


class AmbiguousLicense(BadLicense):
    """Wording in the license can not be unambiguously interoperated, eg 'do no evil' """
    # json license


class JokeLicense(BadLicense):
    """License is a joke or satire"""


class SoftwareSpecific(BadLicense):
    """License wording only applies to a specific project"""

