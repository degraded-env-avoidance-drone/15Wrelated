cmake_minimum_required(VERSION 3.10)

project(livox_sdk2)

set(CMAKE_CXX_STANDARD 17)

message(STATUS "main project dir: " ${PROJECT_SOURCE_DIR})

# For Ubuntu 24.04
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wall -Wno-unknown-pragmas -Wno-sign-compare -Wno-c++20-compat -include cstdint")

if (CMAKE_CROSSCOMPILING)
	set(THREADS_PTHREAD_ARG
		"PLEASE_FILL_OUT-FAILED_TO_RUN"
		CACHE STRING "Result from TRY_RUN" FORCE)
endif()

if (UNIX)
	set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -pthread")
	add_compile_options(-Wno-unknown-pragmas)
endif(UNIX)

add_subdirectory(sdk_core)
# add_subdirectory(samples)
