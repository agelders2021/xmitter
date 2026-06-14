# xmitter firmware — top-level IDF project file.
# Build from inside this directory: `idf.py set-target esp32s3 && idf.py build`.
cmake_minimum_required(VERSION 3.16)

include($ENV{IDF_PATH}/tools/cmake/project.cmake)
project(xmitter_fw)
