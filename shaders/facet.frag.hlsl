// Faceted terrain: each facet has its own flat color (from the map, one per
// triangle) and its own flat normal (from the screen-space derivatives of
// the position), so the ground reads as a patchwork of lit facets.
#include "lighting.hlsli"

StructuredBuffer<uint> face_colors : register(t5, space2);  // After the five sampled textures.

struct PixelInput
{
    float4 position : SV_Position;
    float3 world_pos : TEXCOORD0;
    nointerpolation uint first_face : TEXCOORD1;  // This chunk's first facet in face_colors.
};

float4 main(PixelInput input, uint primitive : SV_PrimitiveID) : SV_Target0
{
    float3 n = normalize(cross(ddy(input.world_pos), ddx(input.world_pos)));
    if (n.y < 0.0)
    {
        n = -n;  // Facets are drawn from both sides; the ground faces up.
    }
    uint rgba = face_colors[input.first_face + primitive];
    float3 srgb = float3(rgba & 0xFFu, (rgba >> 8) & 0xFFu, (rgba >> 16) & 0xFFu) / 255.0;
    return shade(apply_snow(srgb_to_linear(srgb), n, 0.72), n, input.world_pos);
}
