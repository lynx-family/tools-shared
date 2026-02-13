#if defined(_WIN32)
int a = 1;
#elif defined(_WIN64)
int a = 2;
#else
int a = 3;
#endif

#if defined(_WIN32)
int a = 1;
#else
int a = 2;
#endif

#if (_WIN64)
int b = 1;
#else
int b = 2;
#endif

#ifdef _WIN64
int a = 1;
#else
int a = 2;
#endif
