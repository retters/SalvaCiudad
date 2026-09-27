/* Implementation unit for stb_image, limited to the formats glTF embeds.
   Compiled with the library's own flags, like the rest of third_party. */
#define STB_IMAGE_IMPLEMENTATION
#define STBI_ONLY_PNG
#define STBI_ONLY_JPEG
#define STBI_NO_STDIO
#define STBI_NO_LINEAR
#define STBI_NO_HDR
#define STBI_MAX_DIMENSIONS 8192
#include "stb_image.h"
