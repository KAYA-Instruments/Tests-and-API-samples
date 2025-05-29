// stdafx.h : include file for standard system include files,
// or project specific include files that are used frequently, but
// are changed infrequently
//

#pragma once

#ifdef _WIN32
    #include <windows.h>
    #include <conio.h>
    #include "tchar.h"
#else
    #include <stdlib.h>
    #include <errno.h>
    #include <unistd.h>
    #include <stdarg.h>
    #define MAX_PATH 260
    #define Sleep sleep
#endif

#include <stdio.h>
#include <inttypes.h>
#include <time.h>
#include <string.h>

// TODO: reference additional headers your program requires here
