# Главный micropython.cmake — включает все пользовательские C-модули

# Наш GCM-модуль
include(${CMAKE_CURRENT_LIST_DIR}/gcm/micropython.cmake)

# ucryptography (Ed25519, BLAKE2s, RSA-OAEP, ECDSA)
include(/home/tavintavan/esp/ucryptography/micropython.cmake)

# Заглушки для 3DES
add_library(des3_stubs INTERFACE)
target_sources(des3_stubs INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/des3_stubs.c
)
target_link_libraries(usermod INTERFACE des3_stubs)
