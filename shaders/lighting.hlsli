// Stylized lighting shared by the lit pixel shaders: sun with cascaded
// shadows, sky/ground ambient and distance fog. Lighting happens in linear
// space; the result is encoded for the (non-sRGB) swapchain.
#include "scene_common.hlsli"

Texture2D<float4> base_color_tex : register(t0, space2);
Texture2DArray<float> shadow_map : register(t1, space2);
SamplerState base_sampler : register(s0, space2);
SamplerComparisonState shadow_sampler : register(s1, space2);

cbuffer SceneUniforms : register(b0, space3)
{
    float4x4 cascade_matrix[3];
    float4 cascade_split;       // View distances where each cascade ends.
    float4 sun_direction;       // xyz: towards the sun.
    float4 sun_color;           // rgb, linear.
    float4 sky_ambient;         // rgb for normals facing up.
    float4 ground_ambient;      // rgb for normals facing down.
    float4 fog_color;           // rgb; a = density.
    float4 camera_position;     // xyz; w = number of cascades (0 = no shadows).
    float4 shadow_params;       // x = texel size, y = depth bias.
};

cbuffer MaterialUniforms : register(b1, space3)
{
    float4 base_color;
};

float sample_shadow(float3 world_pos, float view_distance, float3 normal)
{
    int count = (int)camera_position.w;
    if (count == 0)
    {
        return 1.0;
    }
    int cascade = count - 1;
    [unroll] for (int i = 2; i >= 0; --i)
    {
        if (i < count && view_distance < cascade_split[i])
        {
            cascade = i;
        }
    }
    if (view_distance >= cascade_split[count - 1])
    {
        return 1.0;  // Beyond the shadow distance.
    }
    // Push the lookup slightly along the normal to avoid self-shadowing.
    float3 offset_pos = world_pos + normal * (0.04 + 0.02 * cascade);
    float4 light = mul(cascade_matrix[cascade], float4(offset_pos, 1.0));
    float2 uv = float2(light.x * 0.5 + 0.5, 0.5 - light.y * 0.5);
    if (any(uv < 0.0) || any(uv > 1.0))
    {
        return 1.0;
    }
    // Reversed depth: larger is closer to the sun.
    float reference = light.z + shadow_params.y;
    float texel = shadow_params.x;
    float lit = 0.0;
    [unroll] for (int y = -1; y <= 1; ++y)
    {
        [unroll] for (int x = -1; x <= 1; ++x)
        {
            lit += shadow_map.SampleCmpLevelZero(shadow_sampler, float3(uv + float2(x, y) * texel, cascade), reference);
        }
    }
    return lit / 9.0;
}

// Lit, fogged color for the swapchain from a linear albedo.
float4 shade(float3 albedo, float3 n, float3 world_pos)
{
    float3 to_camera = camera_position.xyz - world_pos;
    float distance = length(to_camera);

    float3 l = normalize(sun_direction.xyz);
    float n_dot_l = saturate(dot(n, l));
    float shadow = n_dot_l > 0.0 ? sample_shadow(world_pos, distance, n) : 0.0;
    float3 ambient = lerp(ground_ambient.rgb, sky_ambient.rgb, n.y * 0.5 + 0.5);
    float3 color = albedo * (sun_color.rgb * n_dot_l * shadow + ambient);

    float fog = 1.0 - exp2(-fog_color.a * distance * distance);
    color = lerp(color, fog_color.rgb, saturate(fog));
    return float4(linear_to_srgb(tonemap(color)), 1.0);
}
