// One direction of a separable Gaussian blur over the finished scene, used
// behind the pause menu. Drawn with the sky's full-screen triangle.

Texture2D<float4> scene : register(t0, space2);
SamplerState scene_sampler : register(s0, space2);

cbuffer BlurUniforms : register(b0, space3)
{
    float4 step_dim;  // xy: offset between taps in UV; z: darkening (0..1).
};

struct PixelInput
{
    float4 position : SV_Position;
    float2 ndc : TEXCOORD0;
};

float4 main(PixelInput input) : SV_Target0
{
    float2 uv = float2(input.ndc.x * 0.5 + 0.5, 0.5 - input.ndc.y * 0.5);
    // Nine taps; bilinear filtering between them widens the kernel.
    static const float weights[5] = {0.2270270, 0.1945946, 0.1216216, 0.0540541, 0.0162162};
    float3 sum = scene.Sample(scene_sampler, uv).rgb * weights[0];
    [unroll] for (int i = 1; i < 5; ++i)
    {
        float2 o = step_dim.xy * i;
        sum += scene.Sample(scene_sampler, uv + o).rgb * weights[i];
        sum += scene.Sample(scene_sampler, uv - o).rgb * weights[i];
    }
    return float4(sum * (1.0 - step_dim.z), 1.0);
}
