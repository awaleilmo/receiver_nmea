#!/bin/bash
APP_NAME="SeaScope_Receiver"
VERSION="1.0.0"

# Paths
APPDIR=build_linux/${APP_NAME}.AppDir
DIST=dist/${APP_NAME}

# Clean old
rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/bin"

# Build PyInstaller
pyinstaller SeaScope_Receiver.spec

# Copy binary & assets
cp "$DIST" "$APPDIR/usr/bin/"
cp -r UI Assets nmea_data.db "$APPDIR/"
cp build_linux/AppRun "$APPDIR/"
cp build_linux/${APP_NAME}.desktop "$APPDIR/"
cp Assets/logo_ipm.png "$APPDIR/logo_ipm.png"

# Download appimagetool if needed
if [ ! -f build_linux/appimagetool ]; then
    wget -O build_linux/appimagetool https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage
    chmod +x build_linux/appimagetool
fi

# Build AppImage
./build_linux/appimagetool "$APPDIR" "${APP_NAME}-${VERSION}.AppImage"
