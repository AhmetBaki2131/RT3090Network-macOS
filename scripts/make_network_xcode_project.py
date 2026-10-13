#!/usr/bin/env python3
"""Deterministically generate the checked-in native kernel-extension target."""
from pathlib import Path
import json
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
objects = {}

def obj(object_key, isa, **fields):
    import hashlib
    key = hashlib.sha256(object_key.encode()).hexdigest()[:24].upper()
    objects[key] = dict(isa=isa, **fields)
    return key

def emit(value, level=0):
    if isinstance(value, dict):
        return "{\n" + "".join("\t"*(level+1) + str(k) + " = " + emit(v, level+1) + ";\n" for k, v in value.items()) + "\t"*level + "}"
    if isinstance(value, list):
        return "(" + ", ".join(emit(v, level+1) for v in value) + ("," if value else "") + ")"
    return json.dumps(str(value))

def main():
    refs = []
    builds = []
    paths = ["port/rt2860.cpp", "port/RTBSDGlue.cpp", "port/RT3090Network.cpp", "port/rijndael.c", "port/RTTimeout.cpp", "port/ieee80211.c", "port/RTMbuf.cpp", "port/RTIfq.cpp", "port/RTConnection.cpp", "port/ieee80211_input.c", "port/ieee80211_pae_output.c", "port/ieee80211_node.c", "port/ieee80211_proto.c", "port/ieee80211_pae_input.c", "port/ieee80211_mira.c"]
    for folder in ["net80211", "crypto", "sys"]:
        paths += [str(p.relative_to(ROOT)) for p in sorted((ROOT/"vendor/itl80211/openbsd"/folder).glob("*.c"))]
        paths += [str(p.relative_to(ROOT)) for p in sorted((ROOT/"vendor/itl80211/openbsd"/folder).glob("*.cpp"))]
    paths = [p for p in paths if p not in ["vendor/itl80211/openbsd/sys/_task.cpp", "vendor/itl80211/openbsd/crypto/rijndael.c", "vendor/itl80211/openbsd/net80211/CTimeout.cpp", "vendor/itl80211/openbsd/net80211/ieee80211.c", "vendor/itl80211/openbsd/sys/_mbuf.cpp", "vendor/itl80211/openbsd/sys/_ifq.cpp", "vendor/itl80211/openbsd/net80211/ieee80211_input.c", "vendor/itl80211/openbsd/net80211/ieee80211_pae_output.c", "vendor/itl80211/openbsd/net80211/ieee80211_node.c", "vendor/itl80211/openbsd/net80211/ieee80211_proto.c", "vendor/itl80211/openbsd/net80211/ieee80211_pae_input.c", "vendor/itl80211/openbsd/net80211/ieee80211_mira.c"]]
    paths += ["src/rt3090_core.c", "InfoNetwork.plist", "README.md"]
    for path in paths:
        # The BSD compatibility sources use C++ IOKit types, even with a .c suffix.
        kind = "sourcecode.cpp.cpp" if path.endswith((".c", ".cpp")) and path != "src/rt3090_core.c" else "sourcecode.c.c" if path.endswith(".c") else "text.plist.xml" if path.endswith(".plist") else "text"
        ref = obj(path, "PBXFileReference", lastKnownFileType=kind, path=path, sourceTree="<group>")
        refs.append(ref)
        if path.endswith((".c", ".cpp")):
            builds.append(obj(path+" build", "PBXBuildFile", fileRef=ref))
    lib = obj("libkmod", "PBXFileReference", lastKnownFileType="archive.ar", path="vendor/MacKernelSDK/Library/x86_64/libkmod.a", sourceTree="<group>")
    refs.append(lib)
    lib_build = obj("libkmod build", "PBXBuildFile", fileRef=lib)
    product = obj("product", "PBXFileReference", explicitFileType="wrapper.kext", path="RT3090Network.kext", sourceTree="BUILT_PRODUCTS_DIR")
    products = obj("products", "PBXGroup", children=[product], name="Products", sourceTree="<group>")
    main_group = obj("main", "PBXGroup", children=refs+[products], sourceTree="<group>")
    sources = obj("sources", "PBXSourcesBuildPhase", buildActionMask=2147483647, files=builds, runOnlyForDeploymentPostprocessing=0)
    frameworks = obj("frameworks", "PBXFrameworksBuildPhase", buildActionMask=2147483647, files=[lib_build], runOnlyForDeploymentPostprocessing=0)
    resources = obj("resources", "PBXResourcesBuildPhase", buildActionMask=2147483647, files=[], runOnlyForDeploymentPostprocessing=0)
    # Native Xcode kernel-extension product supplies kmod_info and kernel link settings.
    generate = obj("generated include", "PBXShellScriptBuildPhase", buildActionMask=2147483647, files=[], inputPaths=[], outputPaths=[],
        runOnlyForDeploymentPostprocessing=0, shellPath="/bin/sh", shellScript='set -eu\ncd "$PROJECT_DIR"\nif [ ! -f build/generated/FirmwareData.h ]; then\n python3 scripts/prepare_firmware.py --output build/generated/FirmwareData.h\nfi\n', alwaysOutOfDate=1)
    target_configs, project_configs = [], []
    for name in ["Debug", "Release"]:
        settings = dict(RT3090_NETWORK_ENABLED="1", ARCHS="x86_64", SDKROOT="macosx10.13", MACOSX_DEPLOYMENT_TARGET="10.13",
            CLANG_CXX_LANGUAGE_STANDARD="gnu++14", CLANG_CXX_LIBRARY="", CLANG_ENABLE_MODULES="NO",
            GCC_C_LANGUAGE_STANDARD="c99", GCC_ENABLE_KERNEL_DEVELOPMENT="YES",
            GCC_ENABLE_CPP_EXCEPTIONS="NO", GCC_ENABLE_CPP_RTTI="NO", GCC_ENABLE_BUILTIN_FUNCTIONS="NO",
            GCC_PREPROCESSOR_DEFINITIONS=["$(inherited)", "KERNEL=1", "KERNEL_PRIVATE=1", "DRIVER_PRIVATE=1", "IEEE80211_STA_ONLY=1", "_FORTIFY_SOURCE=0", "RT3090_ENABLE_NETWORK_EXPERIMENT=$(RT3090_NETWORK_ENABLED)"],
            GCC_OPTIMIZATION_LEVEL="0" if name=="Debug" else "2", GCC_WARN_ABOUT_RETURN_TYPE="YES_ERROR",
            HEADER_SEARCH_PATHS=["$(PROJECT_DIR)/include", "$(PROJECT_DIR)/port", "$(PROJECT_DIR)/vendor/itl80211/openbsd", "$(PROJECT_DIR)/vendor/itl80211", "$(PROJECT_DIR)/vendor/itl80211/linux", "$(PROJECT_DIR)/build/generated", "$(PROJECT_DIR)/vendor/MacKernelSDK/Headers"],
            KERNEL_EXTENSION_HEADER_SEARCH_PATHS="$(PROJECT_DIR)/vendor/MacKernelSDK/Headers",
            KERNEL_FRAMEWORK_HEADERS="$(PROJECT_DIR)/vendor/MacKernelSDK/Headers",
            LIBRARY_SEARCH_PATHS=["$(PROJECT_DIR)/vendor/MacKernelSDK/Library/x86_64"],
            INFOPLIST_FILE="InfoNetwork.plist", PRODUCT_NAME="RT3090Network", PRODUCT_BUNDLE_IDENTIFIER="org.rt3090.network",
            MODULE_NAME="org.rt3090.network", MODULE_VERSION="0.3.4", WRAPPER_EXTENSION="kext",
            CODE_SIGNING_ALLOWED="NO", CODE_SIGN_IDENTITY="", DEBUG_INFORMATION_FORMAT="dwarf",
            OTHER_CFLAGS=["$(inherited)", "-fno-stack-protector"], OTHER_CPLUSPLUSFLAGS=["$(inherited)", "-fno-stack-protector", "-include", "$(PROJECT_DIR)/port/RTBSDPrefix.hpp", "-mno-red-zone", "-mno-sse", "-mno-sse2", "-mno-mmx"],
            ONLY_ACTIVE_ARCH="NO", SKIP_INSTALL="YES")
        target_configs.append(obj("target "+name, "XCBuildConfiguration", buildSettings=settings, name=name))
        project_configs.append(obj("project "+name, "XCBuildConfiguration", buildSettings={}, name=name))
    target_list = obj("target configs", "XCConfigurationList", buildConfigurations=target_configs, defaultConfigurationIsVisible=0, defaultConfigurationName="Debug")
    project_list = obj("project configs", "XCConfigurationList", buildConfigurations=project_configs, defaultConfigurationIsVisible=0, defaultConfigurationName="Debug")
    target = obj("target", "PBXNativeTarget", buildConfigurationList=target_list, buildPhases=[generate, sources, frameworks, resources], buildRules=[], dependencies=[],
        name="RT3090Network", productName="RT3090Network", productReference=product, productType="com.apple.product-type.kernel-extension")
    project = obj("project", "PBXProject", attributes={"LastUpgradeCheck": "0940"}, buildConfigurationList=project_list,
        compatibilityVersion="Xcode 3.2", developmentRegion="en", hasScannedForEncodings=0, knownRegions=["en"], mainGroup=main_group,
        productRefGroup=products, projectDirPath="", projectRoot="", targets=[target])
    directory = ROOT/"RT3090Network.xcodeproj"
    directory.mkdir(exist_ok=True)
    (directory/"project.pbxproj").write_text("// !$*UTF8*$!\n"+emit(dict(archiveVersion=1, classes={}, objectVersion=46, objects=objects, rootObject=project))+"\n")
    scheme = ET.Element("Scheme", LastUpgradeVersion="0940", version="1.3")
    action = ET.SubElement(scheme,"BuildAction",parallelizeBuildables="YES",buildImplicitDependencies="YES")
    entries = ET.SubElement(action,"BuildActionEntries")
    entry = ET.SubElement(entries,"BuildActionEntry",buildForTesting="YES",buildForRunning="YES",buildForProfiling="YES",buildForArchiving="YES",buildForAnalyzing="YES")
    ET.SubElement(entry,"BuildableReference",BuildableIdentifier="primary",BlueprintIdentifier=target,BuildableName="RT3090Network.kext",BlueprintName="RT3090Network",ReferencedContainer="container:RT3090Network.xcodeproj")
    ET.SubElement(scheme,"AnalyzeAction",buildConfiguration="Debug")
    ET.SubElement(scheme,"ArchiveAction",buildConfiguration="Release",revealArchiveInOrganizer="YES")
    shared = directory/"xcshareddata/xcschemes"
    shared.mkdir(parents=True,exist_ok=True)
    ET.ElementTree(scheme).write(shared/"RT3090Network.xcscheme", encoding="utf-8", xml_declaration=True)

if __name__ == "__main__":
    main()
