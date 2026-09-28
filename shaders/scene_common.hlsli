// Shared declarations for the 3D scene shaders.

// One placed copy of a model, read from a storage buffer by index.
struct InstanceData
{
    float4 row0;  // World matrix rows (affine, 3x4).
    float4 row1;
    float4 row2;
    float4 tint;  // Multiplies the material color.
};

float3 instance_transform(InstanceData inst, float3 p)
{
    float4 v = float4(p, 1.0);
    return float3(dot(inst.row0, v), dot(inst.row1, v), dot(inst.row2, v));
}

float3 instance_rotate(InstanceData inst, float3 n)
{
    // Instances use uniform scale, so the rotation part works for normals.
    return float3(dot(inst.row0.xyz, n), dot(inst.row1.xyz, n), dot(inst.row2.xyz, n));
}

float3 srgb_to_linear(float3 c)
{
    return pow(max(c, 0.0), 2.2);
}

// Filmic curve (ACES, fitted by K. Narkowicz): bright light rolls off
// instead of clipping, so sunlit colors keep their hue.
float3 tonemap(float3 c)
{
    c *= 0.68;  // Exposure.
    return saturate((c * (2.51 * c + 0.03)) / (c * (2.43 * c + 0.59) + 0.14));
}

float3 linear_to_srgb(float3 c)
{
    return pow(saturate(c), 1.0 / 2.2);
}

// Fog of war (phases 32 to 34). The fog texture has one texel per 4 m
// cell: 0 unexplored, 0.5 explored but out of sight, 1 in sight. The
// ceiling texture holds, in coarse cells, the height (in units of 655.35 m)
// under which the fog hides things. `war`: x = texture coordinates per
// meter, y = mode (0 none, 1 static, 2 dynamic), z = height of the band
// over the ceiling where the fog thins out (0: no ceiling), w = unused.
static const float kWarCeilingScale = 655.35;

// One tap; beyond the map's edge nothing was ever explored.
float war_fog_tap(Texture2D<float> fog, SamplerState s, float2 uv)
{
    return all(uv >= 0.0) && all(uv <= 1.0) ? fog.SampleLevel(s, uv, 0.0) : 0.0;
}

float war_fog_value(Texture2D<float> fog, SamplerState s, float2 xz, float4 war)
{
    // A few taps for soft edges instead of 4 m squares.
    float2 uv = xz * war.x;
    float o = 1.6 * war.x;
    float v = war_fog_tap(fog, s, uv) * 0.36;
    v += war_fog_tap(fog, s, uv + float2(o, o)) * 0.16;
    v += war_fog_tap(fog, s, uv + float2(-o, o)) * 0.16;
    v += war_fog_tap(fog, s, uv + float2(o, -o)) * 0.16;
    v += war_fog_tap(fog, s, uv + float2(-o, -o)) * 0.16;
    return v;
}

// How far over the fog's ceiling a point stands, 0..1 (phase 34).
float war_lift(Texture2D<float> ceiling, SamplerState s, float3 world_pos, float4 war)
{
    if (war.z <= 0.0)
    {
        return 0.0;
    }
    float top = ceiling.SampleLevel(s, world_pos.xz * war.x, 0.0) * kWarCeilingScale;
    return saturate((world_pos.y - top) / war.z);
}

// Unexplored ground goes black and what was explored but is out of sight
// goes dim and grey (dynamic fog). What stands over the ceiling shows as a
// dark silhouette in the black and as it is in the grey.
float3 apply_war_fog(float3 color, float value, float lift, float4 war)
{
    if (war.y < 0.5)
    {
        return color;
    }
    float black;
    float dim;
    if (war.y < 1.5)
    {
        black = saturate(1.0 - value);
        dim = 0.0;
    }
    else
    {
        black = saturate(1.0 - 2.0 * value);
        dim = saturate(2.0 - 2.0 * value);
    }
    float luma = dot(color, float3(0.2126, 0.7152, 0.0722));
    float3 dimmed = lerp(color, luma * float3(0.85, 0.92, 1.05), 0.75) * 0.45;
    color = lerp(color, dimmed, dim * (1.0 - lift));
    float3 silhouette = luma * float3(0.16, 0.18, 0.22) + float3(0.012, 0.014, 0.02);
    float3 hidden = lerp(float3(0.006, 0.007, 0.01), silhouette, lift);
    return lerp(color, hidden, black);
}
