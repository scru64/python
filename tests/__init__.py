from __future__ import annotations

import dataclasses


@dataclasses.dataclass
class ExampleNodeSpec:
    node_spec: str
    canonical: str
    spec_type: str
    node_id: int
    node_id_size: int
    node_prev: int


EXAMPLE_NODE_SPECS: list[ExampleNodeSpec] = [
    ExampleNodeSpec(
        node_spec="0/1",
        canonical="0/1",
        spec_type="dec_node_id",
        node_id=0,
        node_id_size=1,
        node_prev=0x0000000000000000,
    ),
    ExampleNodeSpec(
        node_spec="1/1",
        canonical="1/1",
        spec_type="dec_node_id",
        node_id=1,
        node_id_size=1,
        node_prev=0x0000000000800000,
    ),
    ExampleNodeSpec(
        node_spec="0/8",
        canonical="0/8",
        spec_type="dec_node_id",
        node_id=0,
        node_id_size=8,
        node_prev=0x0000000000000000,
    ),
    ExampleNodeSpec(
        node_spec="42/8",
        canonical="42/8",
        spec_type="dec_node_id",
        node_id=42,
        node_id_size=8,
        node_prev=0x00000000002A0000,
    ),
    ExampleNodeSpec(
        node_spec="255/8",
        canonical="255/8",
        spec_type="dec_node_id",
        node_id=255,
        node_id_size=8,
        node_prev=0x0000000000FF0000,
    ),
    ExampleNodeSpec(
        node_spec="0/16",
        canonical="0/16",
        spec_type="dec_node_id",
        node_id=0,
        node_id_size=16,
        node_prev=0x0000000000000000,
    ),
    ExampleNodeSpec(
        node_spec="334/16",
        canonical="334/16",
        spec_type="dec_node_id",
        node_id=334,
        node_id_size=16,
        node_prev=0x0000000000014E00,
    ),
    ExampleNodeSpec(
        node_spec="65535/16",
        canonical="65535/16",
        spec_type="dec_node_id",
        node_id=65535,
        node_id_size=16,
        node_prev=0x0000000000FFFF00,
    ),
    ExampleNodeSpec(
        node_spec="0/23",
        canonical="0/23",
        spec_type="dec_node_id",
        node_id=0,
        node_id_size=23,
        node_prev=0x0000000000000000,
    ),
    ExampleNodeSpec(
        node_spec="123456/23",
        canonical="123456/23",
        spec_type="dec_node_id",
        node_id=123456,
        node_id_size=23,
        node_prev=0x000000000003C480,
    ),
    ExampleNodeSpec(
        node_spec="8388607/23",
        canonical="8388607/23",
        spec_type="dec_node_id",
        node_id=8388607,
        node_id_size=23,
        node_prev=0x0000000000FFFFFE,
    ),
    ExampleNodeSpec(
        node_spec="0x0/1",
        canonical="0/1",
        spec_type="hex_node_id",
        node_id=0,
        node_id_size=1,
        node_prev=0x0000000000000000,
    ),
    ExampleNodeSpec(
        node_spec="0x1/1",
        canonical="1/1",
        spec_type="hex_node_id",
        node_id=1,
        node_id_size=1,
        node_prev=0x0000000000800000,
    ),
    ExampleNodeSpec(
        node_spec="0xb/8",
        canonical="11/8",
        spec_type="hex_node_id",
        node_id=11,
        node_id_size=8,
        node_prev=0x00000000000B0000,
    ),
    ExampleNodeSpec(
        node_spec="0x8f/8",
        canonical="143/8",
        spec_type="hex_node_id",
        node_id=143,
        node_id_size=8,
        node_prev=0x00000000008F0000,
    ),
    ExampleNodeSpec(
        node_spec="0xd7/8",
        canonical="215/8",
        spec_type="hex_node_id",
        node_id=215,
        node_id_size=8,
        node_prev=0x0000000000D70000,
    ),
    ExampleNodeSpec(
        node_spec="0xbaf/16",
        canonical="2991/16",
        spec_type="hex_node_id",
        node_id=2991,
        node_id_size=16,
        node_prev=0x00000000000BAF00,
    ),
    ExampleNodeSpec(
        node_spec="0x10fa/16",
        canonical="4346/16",
        spec_type="hex_node_id",
        node_id=4346,
        node_id_size=16,
        node_prev=0x000000000010FA00,
    ),
    ExampleNodeSpec(
        node_spec="0xcc83/16",
        canonical="52355/16",
        spec_type="hex_node_id",
        node_id=52355,
        node_id_size=16,
        node_prev=0x0000000000CC8300,
    ),
    ExampleNodeSpec(
        node_spec="0xc8cd1/23",
        canonical="822481/23",
        spec_type="hex_node_id",
        node_id=822481,
        node_id_size=23,
        node_prev=0x00000000001919A2,
    ),
    ExampleNodeSpec(
        node_spec="0x26eff5/23",
        canonical="2551797/23",
        spec_type="hex_node_id",
        node_id=2551797,
        node_id_size=23,
        node_prev=0x00000000004DDFEA,
    ),
    ExampleNodeSpec(
        node_spec="0x7c6bc4/23",
        canonical="8154052/23",
        spec_type="hex_node_id",
        node_id=8154052,
        node_id_size=23,
        node_prev=0x0000000000F8D788,
    ),
    ExampleNodeSpec(
        node_spec="v0rbps7ay8ks/1",
        canonical="v0rbps7ay8ks/1",
        spec_type="node_prev",
        node_id=0,
        node_id_size=1,
        node_prev=0x38A9E683BB4425EC,
    ),
    ExampleNodeSpec(
        node_spec="v0rbps7ay8ks/8",
        canonical="v0rbps7ay8ks/8",
        spec_type="node_prev",
        node_id=68,
        node_id_size=8,
        node_prev=0x38A9E683BB4425EC,
    ),
    ExampleNodeSpec(
        node_spec="v0rbps7ay8ks/16",
        canonical="v0rbps7ay8ks/16",
        spec_type="node_prev",
        node_id=17445,
        node_id_size=16,
        node_prev=0x38A9E683BB4425EC,
    ),
    ExampleNodeSpec(
        node_spec="v0rbps7ay8ks/23",
        canonical="v0rbps7ay8ks/23",
        spec_type="node_prev",
        node_id=2233078,
        node_id_size=23,
        node_prev=0x38A9E683BB4425EC,
    ),
    ExampleNodeSpec(
        node_spec="z0jndjt42op2/1",
        canonical="z0jndjt42op2/1",
        spec_type="node_prev",
        node_id=1,
        node_id_size=1,
        node_prev=0x3FF596748EA77186,
    ),
    ExampleNodeSpec(
        node_spec="z0jndjt42op2/8",
        canonical="z0jndjt42op2/8",
        spec_type="node_prev",
        node_id=167,
        node_id_size=8,
        node_prev=0x3FF596748EA77186,
    ),
    ExampleNodeSpec(
        node_spec="z0jndjt42op2/16",
        canonical="z0jndjt42op2/16",
        spec_type="node_prev",
        node_id=42865,
        node_id_size=16,
        node_prev=0x3FF596748EA77186,
    ),
    ExampleNodeSpec(
        node_spec="z0jndjt42op2/23",
        canonical="z0jndjt42op2/23",
        spec_type="node_prev",
        node_id=5486787,
        node_id_size=23,
        node_prev=0x3FF596748EA77186,
    ),
    ExampleNodeSpec(
        node_spec="f2bembkd4zrb/1",
        canonical="f2bembkd4zrb/1",
        spec_type="node_prev",
        node_id=1,
        node_id_size=1,
        node_prev=0x1B844EB5D1AEBB07,
    ),
    ExampleNodeSpec(
        node_spec="f2bembkd4zrb/8",
        canonical="f2bembkd4zrb/8",
        spec_type="node_prev",
        node_id=174,
        node_id_size=8,
        node_prev=0x1B844EB5D1AEBB07,
    ),
    ExampleNodeSpec(
        node_spec="f2bembkd4zrb/16",
        canonical="f2bembkd4zrb/16",
        spec_type="node_prev",
        node_id=44731,
        node_id_size=16,
        node_prev=0x1B844EB5D1AEBB07,
    ),
    ExampleNodeSpec(
        node_spec="f2bembkd4zrb/23",
        canonical="f2bembkd4zrb/23",
        spec_type="node_prev",
        node_id=5725571,
        node_id_size=23,
        node_prev=0x1B844EB5D1AEBB07,
    ),
    ExampleNodeSpec(
        node_spec="mkg0fd5p76pp/1",
        canonical="mkg0fd5p76pp/1",
        spec_type="node_prev",
        node_id=0,
        node_id_size=1,
        node_prev=0x29391373AB449ABD,
    ),
    ExampleNodeSpec(
        node_spec="mkg0fd5p76pp/8",
        canonical="mkg0fd5p76pp/8",
        spec_type="node_prev",
        node_id=68,
        node_id_size=8,
        node_prev=0x29391373AB449ABD,
    ),
    ExampleNodeSpec(
        node_spec="mkg0fd5p76pp/16",
        canonical="mkg0fd5p76pp/16",
        spec_type="node_prev",
        node_id=17562,
        node_id_size=16,
        node_prev=0x29391373AB449ABD,
    ),
    ExampleNodeSpec(
        node_spec="mkg0fd5p76pp/23",
        canonical="mkg0fd5p76pp/23",
        spec_type="node_prev",
        node_id=2248030,
        node_id_size=23,
        node_prev=0x29391373AB449ABD,
    ),
]
