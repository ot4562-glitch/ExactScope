//! Link-time policy for experimental specialized Wasm capability builds.

fn main() {
    println!("cargo:rerun-if-env-changed=CARGO_FEATURE_STATS_SPECIALIZED");
    println!("cargo:rerun-if-env-changed=CARGO_FEATURE_ECON_SPECIALIZED");
    println!("cargo:rerun-if-env-changed=CARGO_CFG_TARGET_ARCH");

    let specialized = std::env::var_os("CARGO_FEATURE_STATS_SPECIALIZED").is_some()
        || std::env::var_os("CARGO_FEATURE_ECON_SPECIALIZED").is_some();
    let wasm32 = std::env::var("CARGO_CFG_TARGET_ARCH").is_ok_and(|arch| arch == "wasm32");
    if specialized && wasm32 {
        // Empirical development boundary on the Statistics-8 conformance/stress
        // suite is between 2 KiB (traps) and 4 KiB (passes). Keep a 4x margin
        // while still fitting static data + stack in one 64 KiB Wasm page.
        println!("cargo:rustc-link-arg=-zstack-size=16384");
        println!("cargo:rustc-link-arg=--max-memory=65536");
    }
}
