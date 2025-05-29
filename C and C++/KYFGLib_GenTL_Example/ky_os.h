#ifndef KY_OS_H__
#define KY_OS_H__

/* Some ad-hoc OS abstractions */
#if defined(_WIN32) || defined(__CYGWIN__)
    #include <Windows.h>
    //#include <winioctl.h>
    //#include <initguid.h>
    #include <process.h>

    // library
    #define ky_lib HMODULE
    #define ky_load_lib(_LIB_, _H_) _H_ = LoadLibraryA(_LIB_)
    #define ky_fn_declare(_FN_)  P##_FN_ _FN_;
    #define ky_fn_load(_TL_,_H_,_FN_) _TL_._FN_ = (P##_FN_)GetProcAddress(_H_, #_FN_);
    #define ky_free_lib(_H_) FreeLibrary(_H_); _H_ = NULL;


#elif defined(__linux) || defined(__APPLE__)
   #include <dlfcn.h>


// library
    #define ky_lib void*
    #define ky_load_lib(_LIB_, _H_) _H_ = dlopen (_LIB_, RTLD_LAZY)
    #define ky_fn_declare(_FN_)  P##_FN_ _FN_;
    #define ky_fn_load(_TL_,_H_,_FN_) _TL_._FN_ = (P##_FN_)dlsym(_H_, #_FN_);
    #define ky_free_lib(_H_) dlclose (_H_); _H_ = NULL;

#endif



#endif // KY_OS_H__
