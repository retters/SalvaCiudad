// Stylized lighting shared by the lit pixel shaders: sun with cascaded
// shadows, sky/ground ambient and distance fog. Lighting happens in linear
// space; the result is encoded for the (non-sRGB) swapchain.
#include "scene_common.hlsli"

Texture2D<float4> base_color_tex : register(t0, space2);
Texture2DArray<float> shadow_map : register(t1, space2);
SamplerState base_sampler : register(s0, space2);
SamplerComparisonState shadow_sampler : register(s1, space2);
// Fog of war (phase 32) and its ceiling (phase 34).
Texture2D<float> war_fog_tex : register(t2, space2);
Texture2D<float> war_ceiling_tex : register(t3, space2);
SamplerState war_sampler : register(s2, space2);
SamplerState war_ceiling_sampler : register(s3, space2);
// The lights of the night (phase 69): what they add at each point of the
// ground around the camera.
Texture2D<float4> light_tex : register(t4, space2);
SamplerState light_sampler : register(s4, space2);

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
    float4 shadow_params;       // x = texel size, y = depth bias, z = snow cover (0..1),
                                // w = 1: the cascades were fitted to another camera (a camera window).
    float4 war_params;          // Fog of war: see apply_war_fog().
    float4 light_params;        // Lights: xy = the world corner of light_tex, z = 1 / the meters it spans,
                                // w = how strong they are (0 by day).
};

// What the lights near a point add to it. The texture keeps the square
// root of a quarter of the light, to tell the dim from the dark, and in its
// alpha how high the lights are ((y + 64) / 512): what is well over them
// (smoke, treetops, a tower's roof) gets less.
float3 point_lights(float3 world_pos)
{
    if (light_params.w <= 0.0)
    {
        return float3(0.0, 0.0, 0.0);
    }
    float2 uv = (world_pos.xz - light_params.xy) * light_params.z;
    if (any(uv < 0.0) || any(uv > 1.0))
    {
        return float3(0.0, 0.0, 0.0);
    }
    float4 v = light_tex.SampleLevel(light_sampler, uv, 0.0);
    float over = world_pos.y - (v.a * 512.0 - 64.0);
    return v.rgb * v.rgb * (4.0 * light_params.w * saturate(1.0 - (over - 3.0) / 9.0));
}

// Snow settles on what faces up, more the deeper it is.
float3 apply_snow(float3 albedo, float3 n, float settle_from)
{
    float snow = shadow_params.z;
    if (snow <= 0.0)
    {
        return albedo;
    }
    float cover = saturate((n.y - settle_from) / (1.0 - settle_from) * 1.6) * saturate(snow * 1.4);
    return lerp(albedo, float3(0.86, 0.9, 0.96), cover);
}

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
    if (shadow_params.w > 0.5)
    {
        // Another camera's cascades: the finest one that holds the point,
        // or no shadow where none does.
        cascade = -1;
        [unroll] for (int k = 2; k >= 0; --k)
        {
            if (k < count)
            {
                float4 at = mul(cascade_matrix[k], float4(world_pos, 1.0));
                if (all(abs(at.xy) < 0.97) && at.z > 0.0 && at.z < 1.0)
                {
                    cascade = k;
                }
            }
        }
        if (cascade < 0)
        {
            return 1.0;
        }
    }
    else
    {
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

// Lit, fogged color for the swapchain from a linear albedo. A landmark
// (1) shows through the fog of war as if it stood over its ceiling. `glow`:
// what shines by itself at night, 1 a lit window, 2 its own color.
float4 shade(float3 albedo, float3 n, float3 world_pos, float landmark = 0.0, float glow = 0.0)
{
    float3 to_camera = camera_position.xyz - world_pos;
    float distance = length(to_camera);

    float3 l = normalize(sun_direction.xyz);
    float n_dot_l = saturate(dot(n, l));
    float shadow = n_dot_l > 0.0 ? sample_shadow(world_pos, distance, n) : 0.0;
    float3 ambient = lerp(ground_ambient.rgb, sky_ambient.rgb, n.y * 0.5 + 0.5);
    float3 color = albedo * (sun_color.rgb * n_dot_l * shadow + ambient + point_lights(world_pos));
    if (glow > 0.5 && light_params.w > 0.0)
    {
        float3 own = glow > 1.5 ? albedo * 2.6 : float3(1.25, 0.82, 0.36);
        color = lerp(color, own, light_params.w);
    }

    float fog = 1.0 - exp2(-fog_color.a * distance * distance);
    color = lerp(color, fog_color.rgb, saturate(fog));
    // The fog of war goes over the haze: what was never seen is the same
    // black near and far, so no shape shows through it.
    if (war_params.y > 0.5)
    {
        float war = war_fog_value(war_fog_tex, war_sampler, world_pos.xz, war_params);
        float lift = max(war_lift(war_ceiling_tex, war_ceiling_sampler, world_pos, war_params), landmark);
        color = apply_war_fog(color, war, lift, war_params);
    }
    return float4(linear_to_srgb(tonemap(color)), 1.0);
}
