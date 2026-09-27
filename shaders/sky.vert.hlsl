// Full-screen triangle for the sky, drawn behind everything.

struct VertexOutput
{
    float4 position : SV_Position;
    float2 ndc : TEXCOORD0;
};

VertexOutput main(uint id : SV_VertexID)
{
    float2 p = float2((id << 1) & 2, id & 2);  // (0,0), (2,0), (0,2)
    VertexOutput output;
    output.ndc = p * 2.0 - 1.0;
    output.position = float4(output.ndc, 0.0, 1.0);  // Depth 0 = far (reversed Z).
    return output;
}
