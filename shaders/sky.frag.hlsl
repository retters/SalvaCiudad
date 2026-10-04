// Sky gradient with a soft sun, matching the fog color at the horizon.
#include "scene_common.hlsli"

cbuffer SkyUniforms : register(b0, space3)
{
    float4x4 inverse_view_proj;
    float4 sun_direction;  // xyz: towards the sun (or the moon); w = stars, 0..1.
    float4 zenith_color;   // rgb, linear.
    float4 horizon_color;  // rgb, linear (same as the fog).
    float4 sun_color;      // rgb, linear; a = how bright its disc is.
};

float hash31(float3 p)
{
    p = frac(p * float3(0.1031, 0.1030, 0.0973));
    p += dot(p, p.yzx + 33.33);
    return frac((p.x + p.y) * p.z);
}

// Stars: one in a few cells of a grid over the directions, each a point.
float stars(float3 dir)
{
    float3 p = dir * 110.0;
    float3 cell = floor(p);
    float pick = hash31(cell);
    if (pick < 0.94)
    {
        return 0.0;
    }
    float3 at = cell + 0.5 + (float3(hash31(cell + 7.0), hash31(cell + 13.0), hash31(cell + 29.0)) - 0.5) * 0.5;
    float d = length(p - at);
    float bright = (pick - 0.94) / 0.06;
    return saturate(1.0 - d / (0.16 + 0.14 * bright)) * (0.35 + 0.65 * bright);
}

struct PixelInput
{
    float4 position : SV_Position;
    float2 ndc : TEXCOORD0;
};

float4 main(PixelInput input) : SV_Target0
{
    float4 near_point = mul(inverse_view_proj, float4(input.ndc, 1.0, 1.0));
    float4 far_point = mul(inverse_view_proj, float4(input.ndc, 0.0001, 1.0));
    float3 dir = normalize(far_point.xyz / far_point.w - near_point.xyz / near_point.w);

    float up = saturate(dir.y);
    float3 color = lerp(horizon_color.rgb, zenith_color.rgb, pow(up, 0.6));
    float sun = saturate(dot(dir, normalize(sun_direction.xyz)));
    color += sun_color.rgb * sun_color.a * (pow(sun, 600.0) * 4.0 + pow(sun, 12.0) * 0.15);
    if (sun_direction.w > 0.0)
    {
        color += stars(dir) * sun_direction.w * saturate(dir.y * 6.0) * float3(0.85, 0.9, 1.0);
    }
    if (dir.y < 0.0)
    {
        color = horizon_color.rgb;  // Below the horizon the fog takes over.
    }
    return float4(linear_to_srgb(tonemap(color)), 1.0);
}
