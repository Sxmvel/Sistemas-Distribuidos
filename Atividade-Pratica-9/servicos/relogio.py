import os
import sys


def ativar_relogio_fino():
    if sys.platform != "win32" or os.getenv("AP9_RELOGIO_FINO", "1") != "1":
        return False
    import ctypes

    return ctypes.WinDLL("winmm").timeBeginPeriod(1) == 0
