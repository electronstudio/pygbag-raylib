#!/bin/bash

export SDKROOT=${SDKROOT:-/opt/python-wasm-sdk}
export CONFIG=${CONFIG:-$SDKROOT/config}

. ${CONFIG}

mkdir -p external

PACKAGE=raylib-python-cffi

echo "

    * building ${PACKAGE} for ${CIVER}, PYBUILD=$PYBUILD => CPython${PYMAJOR}.${PYMINOR}
            PYBUILD=$PYBUILD
            EMFLAVOUR=$EMFLAVOUR
            SDKROOT=$SDKROOT
            SYS_PYTHON=${SYS_PYTHON}

" 1>&2


if pushd $(pwd)/external
then

    if [ -d ${PACKAGE} ]
    then
        pushd $(pwd)/${PACKAGE}
        git restore .
        git pull
    else
        git clone --no-tags --depth 1 --single-branch --branch master https://github.com/electronstudio/raylib-python-cffi ${PACKAGE}
        pushd $(pwd)/${PACKAGE}
        git submodule init
        git submodule update --depth 1
    fi

    # build raylib
    cd raylib-c

        # This patch is required to avoid brinding ASYNCIFY into the SIDE_MODULE (.so)
        # the main module ( pygbag+libpython ) does not use ASYNCIFY so it would not be
        # compatible
        # the only drawback is to use async for game loop ( same as pygame / panda3D , etc )
        # which is not a problem since only async tasks can solve "os threading"
        # correctly on wasm


    patch -p1 <<END
diff --git a/src/platforms/rcore_web.c b/src/platforms/rcore_web.c
index a13f699..52ab2a1 100644
--- a/src/platforms/rcore_web.c
+++ b/src/platforms/rcore_web.c
@@ -153,7 +153,7 @@ bool WindowShouldClose(void)
     // By default, this function is never called on a web-ready raylib example because we encapsulate
     // frame code in a UpdateDrawFrame() function, to allow browser manage execution asynchronously
     // but now emscripten allows sync code to be executed in an interpreted way, using emterpreter!
-    emscripten_sleep(16);
+    // emscripten_sleep(16);
     return false;
 }

END

    patch -p1 <"$GITHUB_WORKSPACE/raylib-web-audio3.diff"

    mkdir build
    cd build
    . ${SDKROOT}/wasm32-${WASM_FLAVOUR}-emscripten-shell.sh
    emcmake cmake .. -DCMAKE_INSTALL_PREFIX=$PREFIX \
     -DCMAKE_BUILD_TYPE=Release \
     -DPLATFORM=Web \
     -DGRAPHICS=GRAPHICS_API_OPENGL_ES3 \
     -DBUILD_EXAMPLES=OFF \
     -DCUSTOMIZE_BUILD=ON \
     -DSUPPORT_FILEFORMAT_JPG=ON \
     -DSUPPORT_FILEFORMAT_FLAC=ON

    emmake make install

    mv -v raylib/libraylib.a ${SDKROOT}/prebuilt/emsdk/libraylib${PYBUILD}.a

    cd ../..

    # fix some includes
    mkdir -p ${PREFIX}/include/GLFW

    cp ${EMSDK}/upstream/emscripten/system/include/GLFW/glfw3.h ${PREFIX}/include/GLFW/

    cp physac/src/physac.h ${PREFIX}/include/
    cp raygui/src/raygui.h ${PREFIX}/include/

    # build it

    ${SDKROOT}/python3-wasm setup.py bdist_wheel --py-limited-api=cp310


    popd
fi
