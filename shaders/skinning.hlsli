// Shared declarations for animated characters.

// One character on screen; matches GpuCharacter in scene_renderer.cpp.
struct CharacterData
{
    float4 row0;  // World matrix rows (affine, 3x4).
    float4 row1;
    float4 row2;
    uint4 anim;   // x: first bone matrix of the clip, y: frames, z: joints, w: palette.
    float4 extra; // x: frame position (frames, fractional).
};

// Baked skin matrices, three rows (float4) each, frame-major.
float3x4 bone_matrix(StructuredBuffer<float4> bones, uint first, uint joints, uint frame, uint joint)
{
    uint i = (first + frame * joints + joint) * 3;
    return float3x4(bones[i], bones[i + 1], bones[i + 2]);
}

// Blends the up-to-four bone matrices of a vertex, interpolating between
// the two nearest baked frames.
float3x4 skin_matrix(StructuredBuffer<float4> bones, CharacterData c, uint4 joints, float4 weights)
{
    uint frames = max(c.anim.y, 1u);
    float position = c.extra.x;
    uint f0 = ((uint)floor(position)) % frames;
    uint f1 = (f0 + 1) % frames;
    float t = frac(position);
    float3x4 m = (float3x4)0;
    [unroll] for (int k = 0; k < 4; ++k)
    {
        if (weights[k] > 0.0)
        {
            float3x4 a = bone_matrix(bones, c.anim.x, c.anim.z, f0, joints[k]);
            float3x4 b = bone_matrix(bones, c.anim.x, c.anim.z, f1, joints[k]);
            m += (a + (b - a) * t) * weights[k];
        }
    }
    return m;
}

float3 character_transform(CharacterData c, float3 p)
{
    float4 v = float4(p, 1.0);
    return float3(dot(c.row0, v), dot(c.row1, v), dot(c.row2, v));
}

float3 character_rotate(CharacterData c, float3 n)
{
    return float3(dot(c.row0.xyz, n), dot(c.row1.xyz, n), dot(c.row2.xyz, n));
}
