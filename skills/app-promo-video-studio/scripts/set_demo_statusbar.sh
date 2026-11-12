#!/usr/bin/env bash
# set_demo_statusbar.sh - give an emulator a clean marketing status bar before capture.
# Fixed clock 12:00, full wifi/signal/battery, no notification icons.
# Usage: ADB=/path/to/adb SERIAL=emulator-5554 ./set_demo_statusbar.sh
set -euo pipefail
ADB="${ADB:-adb}"; SERIAL="${SERIAL:-emulator-5554}"
R(){ "$ADB" -s "$SERIAL" shell "$@" >/dev/null 2>&1; }
R settings put global sysui_demo_allowed 1
R am broadcast -a com.android.systemui.demo -e command enter
R am broadcast -a com.android.systemui.demo -e command clock -e hhmm 1200
R am broadcast -a com.android.systemui.demo -e command battery -e level 100 -e plugged false
R am broadcast -a com.android.systemui.demo -e command network -e wifi show -e level 4
R am broadcast -a com.android.systemui.demo -e command network -e mobile show -e datatype none -e level 4
R am broadcast -a com.android.systemui.demo -e command notifications -e visible false
echo "demo status bar set on $SERIAL (exit with: am broadcast -a com.android.systemui.demo -e command exit)"
