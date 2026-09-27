// Shared by the terrain and water shaders: map heights and chunk data.

// One square of 64 x 64 cells; matches GpuChunk in scene_renderer.cpp.
struct ChunkData
{
    int4 origin;  // x, z: first vertex; w: unused.
    float4 bounds;
};

// Heights are 16-bit centimeters, two per uint.
float map_height(StructuredBuffer<uint> heights, int vertices, int x, int z)
{
    x = clamp(x, 0, vertices - 1);
    z = clamp(z, 0, vertices - 1);
    uint index = (uint)(z * vertices + x);
    uint word = heights[index >> 1];
    uint cm = (index & 1) != 0 ? (word >> 16) : (word & 0xFFFF);
    return (float)cm * 0.01;
}

// Water surface of a cell in meters, or 0 when dry.
float cell_water(StructuredBuffer<uint> water, int cells, int x, int z)
{
    if (x < 0 || z < 0 || x >= cells || z >= cells)
    {
        return 0.0;
    }
    uint index = (uint)(z * cells + x);
    uint word = water[index >> 1];
    uint cm = (index & 1) != 0 ? (word >> 16) : (word & 0xFFFF);
    return (float)cm * 0.01;
}
