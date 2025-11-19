#!/usr/bin/env python3

# pyright: strict

import argparse
import collections.abc
import datetime
import gzip
import plistlib
import re
import sys
import typing

import lxml.etree
import requests


class FormatError(Exception):
    pass


# Returns the OS version as it appears in a sucatalog URL given its year of
# release. Note that macOS 11 appears as 10.16 in sucatalog URLs.
def _year_to_os_version(year: int) -> str:
    if year >= 2025:
        # macOS ≥ 26
        return str(year - 1999)
    if year >= 2021:
        # macOS ≥ 12
        return str(year - 2009)
    if year >= 2013:
        # macOS ≥ 10.9
        return "10." + str(year - 2004)
    return {2012: "mountainlion", 2011: "lion", 2009: "snowleopard", 2007: "leopard"}[
        year
    ]


# https://stackoverflow.com/questions/51418142. This is used because the
# arguments accepted by _year_to_os_version are “sparse” in that 2010 and 2008
# are not accepted.
def _try_iterate(
    callable: collections.abc.Callable[..., typing.Any],
    iterator: collections.abc.Iterable[typing.Any],
    *exceptions: type[BaseException],
    **kwargs: typing.Any,
) -> typing.Any:
    for element in iterator:
        try:
            yield callable(element, **kwargs)
        except exceptions:
            pass


# Returns the sucatalog URL for a desktop macOS version released in |year|, on
# the provided release track. Known values for |track| are "seed" and "beta", or
# it can be left at None for the normal release track.
#
# Example: in 2022, with track="seed", this returns
# https://swscan.apple.com/content/catalogs/others/index-13seed-13-12-10.16-10.15-10.14-10.13-10.12-10.11-10.10-10.9-mountainlion-lion-snowleopard-leopard.merged-1.sucatalog.gz
def _guess_sucatalog_url_for_year(year: int, track: str | None = None) -> str:
    os_versions = list(
        _try_iterate(_year_to_os_version, range(year, 2006, -1), KeyError)
    )
    if year == 2025 and track == "beta":
        # For the beta track (but not the seed track), macOS 26 is represented
        # by “16” in the sucatalog URL.
        os_versions[0] = "16"
    if track is not None:
        os_versions.insert(0, os_versions[0] + track)
    os_versions_string = "-".join(os_versions)
    return (
        "https://swscan.apple.com/content/catalogs/others/index-"
        + os_versions_string
        + ".merged-1.sucatalog.gz"
    )


# If |year| is not None, calls _guess_sucatalog_url_for_year directly and
# returns a single-element tuple containing the result.
#
# Otherwise, returns two URLs, the first working one of which is likely to be
# the most current sucatalog URL, given a correctly-set system clock, on the
# provided release track. The first URL corresponds to the current year’s OS
# release, or expected OS release. In case the expected yearly OS release hasn’t
# yet occurred for the current year, the second URL corresponds to the previous
# year.
def guess_sucatalog_urls(
    year: int | None = None, track: str | None = None
) -> tuple[str, ...]:
    if year is None:
        year = datetime.datetime.now().year
        return (
            _guess_sucatalog_url_for_year(year, track),
            _guess_sucatalog_url_for_year(year - 1, track),
        )

    return (_guess_sucatalog_url_for_year(year, track),)


def sucatalog_to_full_os_installers(
    session: requests.Session, sucatalog_urls: tuple[str, ...]
) -> dict[str, dict[str, typing.Any]]:
    _LOCALIZATION_KEYS = ("English", "en", "en_US")

    sucatalog_response = None
    for sucatalog_url in sucatalog_urls:
        sucatalog_response = session.get(sucatalog_url)
        try:
            sucatalog_response.raise_for_status()
        except requests.HTTPError:
            # Try the next URL. If all URLs resulted in this error, another
            # raise_for_status outside of this retry loop will propagate the
            # exception.
            continue

        # Success
        break

    assert sucatalog_response is not None
    sucatalog_response.raise_for_status()

    sucatalog_response_content_encoding = sucatalog_response.headers.get(
        "content-encoding"
    )
    if (
        sucatalog_response.content[:2] == b"\x1f\x8b"
        and sucatalog_response_content_encoding is not None
        and sucatalog_response_content_encoding.lower() == "x-gzip"
    ):
        # Before urllib3 2.1.0, Content-Encoding: x-gzip was not automatically
        # decoded. urllib3/urllib3 issue 3174, pull request 3176, commit
        # 5fc48e711b33. There were API changes between urllib3 1.x and 2.0 which
        # may cause some installations to remain on the older version, so this
        # code may conceivably run with urllib3 1.x, which does not handle
        # x-gzip, and urllib3 2.1 or later, which do. Since urllib3’s behavior
        # is unknown, sniff out the gzip magic and assume that it was not
        # decoded if Content-Encoding: x-gzip is present. This is not a general
        # solution (it’s not correct for gzipped content served with another
        # layer of gzip via Content-Encoding), but it’ll do in this case, where
        # the plist content will never validly begin with the gzip magic number.
        #
        # When urllib3 2.1 can be assured, this workaround can be removed.
        sucatalog_response_content = gzip.decompress(sucatalog_response.content)
    else:
        sucatalog_response_content = sucatalog_response.content

    sucatalog_plist = plistlib.loads(sucatalog_response_content)

    if sucatalog_plist["CatalogVersion"] != 2:
        raise FormatError("CatalogVersion", sucatalog_plist["CatalogVersion"])

    out_products: dict[str, dict[str, typing.Any]] = {}
    for product_key, product in sucatalog_plist.get("Products", {}).items():
        if "InstallAssistantPackageIdentifiers" in product.get("ExtendedMetaInfo", {}):
            post_date = product["PostDate"]

            localization_key = None
            distribution_url = None
            for localization_key in _LOCALIZATION_KEYS:
                distribution_url = product["Distributions"].get(localization_key)
                if distribution_url is not None:
                    break

            assert localization_key is not None
            assert distribution_url is not None
            distribution_response = session.get(distribution_url)
            distribution_response.raise_for_status()

            distribution_xml = lxml.etree.fromstring(
                distribution_response.content
            )  # pyright: ignore[reportCallIssue]
            if distribution_xml.tag not in ("installer", "installer-gui-script"):
                raise FormatError("distribution_xml.tag", distribution_xml.tag)

            title_xml = distribution_xml.find("title")
            assert title_xml is not None
            title = title_xml.text
            if title == "SU_TITLE":
                title = None

            distribution_auxinfo_dict_xml = distribution_xml.find("auxinfo/dict")
            assert distribution_auxinfo_dict_xml is not None
            distribution_auxinfo_dict: dict[str, str] = {}
            key = None
            for element in distribution_auxinfo_dict_xml:
                if key is None:
                    if element.tag != "key":
                        raise FormatError("element.tag", element.tag)
                    key = element.text
                else:
                    if element.tag != "string":
                        raise FormatError("element.tag", element.tag)
                    assert element.text is not None
                    distribution_auxinfo_dict[key] = element.text
                    key = None
            if key is not None:
                raise FormatError("key", key)

            version: str | None = distribution_auxinfo_dict["VERSION"]
            if version == "SU_VERSION":
                version = None

            build = distribution_auxinfo_dict["BUILD"]
            assert build is not None

            package_filenames: tuple[str, ...] = ("InstallAssistant.pkg",)

            if title is None or version is None:
                smd_response = session.get(product["ServerMetadataURL"])
                smd_response.raise_for_status()

                smd_plist = plistlib.loads(smd_response.content)

                version = smd_plist["CFBundleShortVersionString"]
                assert version is not None
                title = smd_plist["localization"][localization_key]["title"]

                package_filenames = (
                    "AppleDiagnostics.chunklist",
                    "AppleDiagnostics.dmg",
                    "BaseSystem.chunklist",
                    "BaseSystem.dmg",
                    "InstallAssistantAuto.pkg",
                    "InstallESDDmg.pkg",
                )

            package_urls: list[str] = []
            for package in product["Packages"]:
                package_url = package["URL"]
                # TODO: Fish the list of packages out of distribution's
                # (root)/choice id="InstallAssistantShell"? Those <pkg-ref id>
                # ids can be associated to fullly qualified identifiers via
                # <pkg-ref id packageIdentifier> packageIdentifier attributes at
                # the (root) OR the <pkg-ref> later in the distribution whose
                # content ties it to a filename. But if going via
                # InstallAssistantShell, that would pull in unnecessary things
                # like OSInstall.mpkg. Seems like a lot of work and not a lot of
                # certainty about how to do it correctly. Maybe the hard-code
                # here is better.
                #
                # Some packages carry package['Digest'] which contains 160 bits
                # like SHA-1. I like verifying things, so what is this? Well,
                # it’s not the SHA-1 of the file contents. But if you look
                # inside at the file contents, you’ll find that same digest
                # value somewhere. It’s the xar checksum! You can find it by
                # taking header_len from big-endian uint16 at 0x4 and
                # compressed_toc_len from big-endian uint64 at 0x8, and
                # checksum_alg from uint8 at 0x18 (1 = SHA-1), and then looking
                # for the digest at offset header_len + compressed_toc_len. The
                # checksum just wraps the zlib-compressed xar TOC, which is
                # compressed_toc_len bytes starting at offset header_len. The
                # TOC should contain checksums of other archive content. But
                # this isn’t particularly interesting, and it leaves some parts
                # of the file unprotected, including the header, and the
                # polyglot tacked-on koly trailer (if any, for
                # InstallAssistant.pkg/InstallESD.dmg hybrid polyglot files).
                #
                # If you are (as I am) interested in a project to verify things,
                # consider the integrity data in integrityDataV1 (chunklist)
                # format from package['IntegrityDataURL']. See
                # https://github.com/hack-different/go-aapl-integrity.
                if package_url.endswith(package_filenames):
                    package_urls.append(package_url)

            build_match = re.match(r"(\d+)([A-Z])(\d+)([a-z])$", build, re.ASCII)
            if build_match is None:
                build_match = re.match(r"(\d+)([A-Z])(\d+)$", build, re.ASCII)
                assert build_match is not None
            build_comp = list(build_match.groups())
            build_comp[0] = int(build_comp[0])
            build_comp[2] = int(build_comp[2])

            out_products[product_key] = {
                "title": title,
                "version": version,
                "version_comp": [int(x) for x in version.split(".")],
                "build": build,
                "build_comp": build_comp,
                "post_date": post_date,
                "package_urls": package_urls,
            }

    return out_products


def main(args: list[str]) -> int | None:
    parser = argparse.ArgumentParser()
    parser_track_group = parser.add_mutually_exclusive_group()
    parser_track_group.add_argument("--track", default="seed")
    parser_track_group.add_argument("--no-track", action="store_true")
    parser.add_argument("--year", type=int)
    parser.add_argument("--sucatalog-url")
    parsed = parser.parse_args(args)

    with requests.Session() as session:
        sucatalog_urls = (
            (parsed.sucatalog_url,)
            if parsed.sucatalog_url is not None
            else guess_sucatalog_urls(
                year=parsed.year, track=None if parsed.no_track else parsed.track
            )
        )
        products = sucatalog_to_full_os_installers(session, sucatalog_urls)

        for product_key, product in sorted(
            products.items(),
            key=lambda item: (item[1]["version_comp"], item[1]["build_comp"]),
        ):
            print(
                "%-5s  %-7s  %-8s  %-10s  %s"
                % (
                    product_key,
                    product["version"],
                    product["build"],
                    product["post_date"].strftime("%Y-%m-%d"),
                    product["title"],
                )
            )
            for package_url in product["package_urls"]:
                print("  %s" % package_url)

    return None


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
