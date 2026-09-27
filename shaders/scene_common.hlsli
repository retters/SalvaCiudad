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

float3 linear_to_srgb(float3 c)
{
    return pow(saturate(c), 1.0 / 2.2);
}
