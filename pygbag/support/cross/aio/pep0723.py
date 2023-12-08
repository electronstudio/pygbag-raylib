#
# https://peps.python.org/pep-0722/ – Dependency specification for single-file scripts
# https://peps.python.org/pep-0723
# https://peps.python.org/pep-0508/ – Dependency specification for Python Software Packages
# https://setuptools.pypa.io/en/latest/userguide/ext_modules.html
#

import sys
import os
from pathlib import Path
import glob

import re

print(sys.path)
import tomllib

import json

import importlib
import installer
import pyparsing
from packaging.requirements import Requirement

from aio.filelike import fopen

import platform
import platform_wasm.todo


# TODO: maybe control wheel cache with $XDG_CACHE_HOME/pip


# store installed wheel somewhere
env = Path(os.getcwd()) / "build" / "env"
env.mkdir(parents=True, exist_ok=True)

# we want host to load wasm packages too
# so make pure/bin folder first for imports

if env.as_posix() not in sys.path:
    sys.path.insert(0, env.as_posix())

sconf = __import__("sysconfig").get_paths()
sconf["purelib"] = sconf["platlib"] = env.as_posix()

if sconf["platlib"] not in sys.path:
    sys.path.append(sconf["platlib"])

PATCHLIST = []
HISTORY = []


class Config:
    READ_722 = False
    READ_723 = True
    BLOCK_RE_722 = r"(?i)^#\s+script\s+dependencies:\s*$"
    BLOCK_RE_723 = r"(?m)^# /// (?P<type>[a-zA-Z0-9-]+)$\s(?P<content>(^#(| .*)$\s)+)^# ///$"
    PKG_INDEXES = []
    REPO_INDEX = "index.json"
    REPO_DATA = "repodata.json"
    repos = []
    pkg_repolist = []
    dev_mode = ".-X.dev." in ".".join([""] + sys.orig_argv + [""])

    mapping = {
        "pygame": "pygame.base",
        "pygame_ce": "pygame.base",
        "python_i18n": "i18n",
        "pillow": "PIL",
    }


def read_dependency_block_722(code):
    # Skip lines until we reach a dependency block (OR EOF).
    has_block = False
    # Read dependency lines until we hit a line that doesn't
    # start with #, or we are at EOF.
    for line in code.split("\n"):
        if not has_block:
            if re.match(Config.BLOCK_RE_722, line):
                has_block = True
            continue

        if not line.startswith("#"):
            break
        # Remove comments. An inline comment is introduced by
        # a hash, which must be preceded and followed by a
        # space.
        line = line[1:].split(" # ", maxsplit=1)[0]
        line = line.strip()
        # Ignore empty lines
        if not line:
            continue
        # Try to convert to a requirement. This will raise
        # an error if the line is not a PEP 508 requirement
        yield Requirement(line)


def read_dependency_block_723(code):
    # Skip lines until we reach a dependency block (OR EOF).
    has_block = False

    content = []
    for line in code.split("\n"):
        if not has_block:
            if line.strip() == "# /// pyproject":
                has_block = True
            continue

        if not line.startswith("#"):
            break

        if line.strip() == "# ///":
            break

        content.append(line[2:])
    struct = tomllib.loads("\n".join(content))

    print(json.dumps(struct, sort_keys=True, indent=4))

    project = struct.get("project", {"dependencies": []})
    for dep in project.get("dependencies", []):
        yield dep


def read_dependency_block_723x(script):
    name = "pyproject"
    matches = list(filter(lambda m: m.group("type") == name, re.finditer(Config.BLOCK_RE_723, script)))
    if len(matches) > 1:
        raise ValueError(f"Multiple {name} blocks found")
    elif len(matches) == 1:
        print(tomllib.loads(matches[0]))
        yield "none"
    else:
        return None


def install(pkg_file, sconf=None):
    global HISTORY
    from installer import install
    from installer.destinations import SchemeDictionaryDestination
    from installer.sources import WheelFile

    # Handler for installation directories and writing into them.
    destination = SchemeDictionaryDestination(
        sconf or __import_("sysconfig").get_paths(),
        interpreter=sys.executable,
        script_kind="posix",
    )

    try:
        with WheelFile.open(pkg_file) as source:
            install(
                source=source,
                destination=destination,
                # Additional metadata that is generated by the installation tool.
                additional_metadata={
                    "INSTALLER": b"pygbag",
                },
            )
        if pkg_file not in HISTORY:
            HISTORY.append(pkg_file)
            importlib.invalidate_caches()
        print(f"142: {pkg_file} installed")
    except FileExistsError as ex:
        print(f"38: {pkg_file} already installed (or partially)", ex)
    except Exception as ex:
        pdb(f"82: cannot install {pkg_file}")
        sys.print_exception(ex)


async def async_imports_init():
    ...


#    see pythonrc
#            if not len(Config.repos):
#                for cdn in (Config.PKG_INDEXES or PyConfig.pkg_indexes):
#                    async with platform.fopen(Path(cdn) / Config.REPO_DATA) as source:
#                        Config.repos.append(json.loads(source.read()))
#
#                DBG("1203: FIXME (this is pyodide maintened stuff, use PEP723 asap) referenced packages :", len(cls.repos[0]["packages"]))
#


async def async_repos():
    abitag = f"cp{sys.version_info.major}{sys.version_info.minor}"

    apitag = __import__("sysconfig").get_config_var("HOST_GNU_TYPE")
    apitag = apitag.replace("-", "_")
    print("163: async_repos", Config.PKG_INDEXES)
    for repo in Config.PKG_INDEXES:
        if apitag.find("mvp") > 0:
            idx = f"{repo}index.json"
        else:
            idx = f"{repo}index-bi.json"
        async with fopen(idx, "r", encoding="UTF-8") as index:
            try:
                data = index.read()
                if isinstance(data, bytes):
                    data = data.decode()
                data = data.replace("<abi>", abitag)
                data = data.replace("<api>", apitag)
                repo = json.loads(data)
            except:
                pdb(f"110: {repo=}: malformed json index {data}")
                continue
            if repo not in Config.pkg_repolist:
                Config.pkg_repolist.append(repo)

    repo = None
    if Config.dev_mode > 0:
        for idx, repo in enumerate(Config.pkg_repolist):
            try:
                repo["-CDN-"] = Config.PKG_INDEXES[idx]
            except Exception as e:
                sys.print_exception(e)

    if not aio.cross.simulator:
        import platform

        print("193:", platform.window.location.href)
        if platform.window.location.href.startswith("http://localhost:8"):
            for idx, repo in enumerate(Config.pkg_repolist):
                repo["-CDN-"] = "http://localhost:8000/archives/repo/"
        elif platform.window.location.href.startswith("https://pmp-p.ddns.net/pygbag"):
            for idx, repo in enumerate(Config.pkg_repolist):
                repo["-CDN-"] = "https://pmp-p.ddns.net/archives/repo/"
        elif platform.window.location.href.startswith("http://192.168.1.66/pygbag"):
            for idx, repo in enumerate(Config.pkg_repolist):
                repo["-CDN-"] = "http://192.168.1.66/archives/repo/"
    if repo:
        print(
            f"""

===============  REDIRECTION TO DEV HOST {repo['-CDN-']}  ================
{abitag=}
{apitag=}

"""
        )


async def install_pkg(sysconf, wheel_url, wheel_pkg):
    target_filename = f"/tmp/{wheel_pkg}"
    async with fopen(wheel_url, "rb") as pkg:
        with open(target_filename, "wb") as target:
            target.write(pkg.read())
    install(target_filename, sysconf)


def do_patches():
    global PATCHLIST
    # apply any patches
    while len(PATCHLIST):
        dep = PATCHLIST.pop(0)
        print(f"254: patching {dep}")
        try:
            import platform

            platform.patches.pop(dep)()
        except Exception as e:
            sys.print_exception(e)


# FIXME: HISTORY and invalidate caches
async def pip_install(pkg, sysconf={}):
    global sconf
    if pkg in HISTORY:
        return

    print("253: searching", pkg)

    if not sysconf:
        sysconf = sconf

    wheel_url = ""

    # hack for WASM wheel repo
    if pkg.lower() in Config.mapping:
        pkg = Config.mapping[pkg.lower()]
        if pkg in HISTORY:
            return
        print("279: package renamed to", pkg)

    if pkg in platform.patches:
        if not pkg in PATCHLIST:
            PATCHLIST.append(pkg)

    for repo in Config.pkg_repolist:
        if pkg in repo:
            wheel_url = f"{repo['-CDN-']}{repo[pkg]}#"

    # try to get a pure python wheel from pypi
    if not wheel_url:
        try:
            async with fopen(f"https://pypi.org/simple/{pkg}/") as html:
                if html:
                    for line in html.readlines():
                        if line.find("href=") > 0:
                            if line.find("-py3-none-any.whl") > 0:
                                wheel_url = line.split('"', 2)[1]
                else:
                    print("283: ERROR: cannot find package :", pkg)
        except FileNotFoundError:
            print("285: ERROR: cannot find package :", pkg)
            return

        except:
            print("289: ERROR: cannot find package :", pkg)
            return

    if wheel_url:
        try:
            wheel_pkg, wheel_hash = wheel_url.rsplit("/", 1)[-1].split("#", 1)
            await install_pkg(sysconf, wheel_url, wheel_pkg)
            if pkg not in HISTORY:
                HISTORY.append(pkg)
        except:
            print("299: INVALID", pkg, "from", wheel_url)


PYGAME = 0


async def parse_code(code, env):
    global PATCHLIST, PYGAME

    maybe_missing = []

    if Config.READ_722:
        for req in read_dependency_block_722(code):
            pkg = str(req)
            if (env / pkg).is_dir():
                print("found in env :", pkg)
                continue
            elif pkg not in maybe_missing:
                # do not change case ( eg PIL )
                maybe_missing.append(pkg.lower().replace("-", "_"))

    if Config.READ_723:
        for req in read_dependency_block_723(code):
            pkg = str(req)
            if (env / pkg).is_dir():
                print("found in env :", pkg)
                continue
            elif pkg not in maybe_missing:
                # do not change case ( eg PIL )
                maybe_missing.append(pkg.lower().replace("-", "_"))

    still_missing = []

    import platform

    for dep in maybe_missing:
        if dep in platform.patches:
            PATCHLIST.append(dep)

        # special case of pygame code in pygbag site-packages
        if dep == "pygame.base" and not PYGAME:
            PYGAME = 1
            still_missing.append(dep)
            continue

        if not importlib.util.find_spec(dep) and dep not in still_missing:
            still_missing.append(dep)
        else:
            print("found in path :", dep)

    return still_missing


# parse_code does the patching
# this is not called by pythonrc
async def check_list(code=None, filename=None):
    global PATCHLIST, async_imports_init, async_repos, env, sconf
    print()
    print("-" * 11, "computing required packages", "-" * 10)

    # pythonrc is calling aio.pep0723.parse_code not check_list
    # so do patching here
    patchlevel = platform_wasm.todo.patch()
    if patchlevel:
        print("264:parse_code() patches loaded :", list(patchlevel.keys()))
        platform_wasm.todo.patch = lambda: None
        # and only do that once and for all.
        await async_imports_init()
        await async_repos()
        del async_imports_init, async_repos

    # mandatory
    importlib.invalidate_caches()

    if code is None:
        code = open(filename, "r").read()

    still_missing = await parse_code(code, env)

    # is there something to do ?
    if len(still_missing):
        importlib.invalidate_caches()

        # TODO: check for possible upgrade of env/* pkg

        maybe_missing = still_missing
        still_missing = []

        for pkg in maybe_missing:
            hit = ""
            for repo in Config.pkg_repolist:
                wheel_pkg = repo.get(pkg, "")
                if wheel_pkg:
                    wheel_url = repo["-CDN-"] + "/" + wheel_pkg
                    wheel_pkg = wheel_url.rsplit("/", 1)[-1]
                    await install_pkg(sconf, wheel_url, wheel_pkg)
                    hit = pkg

            if len(hit):
                print("found on pygbag repo and installed to env :", hit)
            else:
                still_missing.append(pkg)

        for pkg in still_missing:
            di = f"{(env / pkg).as_posix()}-*.dist-info"
            gg = glob.glob(di)
            if gg:
                print("found in env :", gg[0].rsplit("/", 1)[-1])
                continue

            pkg_final = pkg.replace("-", "_")
            if (env / pkg_final).is_dir():
                print("found in env :", pkg)
                continue
            await pip_install(pkg_final, sconf)

    # wasm compilation
    if not aio.cross.simulator:
        import platform
        import asyncio

        platform.explore(sconf["platlib"])
        await asyncio.sleep(0)

    do_patches()

    print("-" * 40)
    print()

    return still_missing


# aio.pep0723
