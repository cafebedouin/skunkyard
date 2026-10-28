//! Three-way agreement run (2026-10-28): the Rust side of the SLH-DSA-SHA2-128s conformance rig.
//!
//! A thin wrapper over RustCrypto's `slh-dsa` crate. It reads the same files the Scala harness
//! (`skunks/policy/6-rekey/slhdsa/SlhDsaRunner.scala`, commands `digests` / `verify-ext` / `acvp` / `negatives`) and the
//! noble scripts (`skunks/pqwallet/scripts/kat.ts`, `diff-sign.ts`) read and write, so one implementation's
//! signatures can be judged by the other two and every verdict lines up by name or spend index. No new cryptography:
//! the message convention is the rig's (pure SLH-DSA, empty context, over the 32-byte spend digest the harness wrote).
//!
//! Commands (run from `skunks/pqwallet/rust`, paths relative to the repository root or absolute):
//!   kat <acvp dir>                              NIST ACVP keyGen / sigGen / sigVer, SLH-DSA-SHA2-128s (kat.ts's checks)
//!   acvp-cases <cases.json> <out.json>          the 56 cases the script judged, M' as framed, through the internal interface
//!   sign <keys.json> <digests.json> <out.json>  sign the harness digests (every fourth spend randomized, as diff-sign.ts)
//!   verify <sigs.json> <out.json>               judge external signatures and their flipped copies (verify-ext's positions)
//!   negatives <neg.json> <two_outputs_digest> <second_box_digest> <prior-out.json> <out.json>
//!                                               judge the structural negatives; join with the script's and BouncyCastle's verdicts
use serde_json::{json, Value};
use slh_dsa::{Sha2_128s, Signature, SigningKey, VerifyingKey};
use std::{fs, process, time::Instant};

type P = Sha2_128s;
const SIG_LEN: usize = 7856;
const PS: &str = "SLH-DSA-SHA2-128s";
const CRATE_VERSION: &str = "0.2.0-rc.5"; // pinned in Cargo.toml; the printed line names it

fn unhex(s: &str) -> Vec<u8> { hex::decode(s).unwrap_or_else(|e| { eprintln!("bad hex: {e}"); process::exit(2) }) }
fn hx(b: &[u8]) -> String { hex::encode(b) }
fn read_json(p: &str) -> Value {
    let text = fs::read_to_string(p).unwrap_or_else(|e| { eprintln!("read {p}: {e}"); process::exit(2) });
    serde_json::from_str(&text).unwrap_or_else(|e| { eprintln!("parse {p}: {e}"); process::exit(2) })
}
fn write_json(p: &str, v: &Value) { fs::write(p, serde_json::to_string(v).unwrap()).unwrap_or_else(|e| { eprintln!("write {p}: {e}"); process::exit(2) }) }
fn s<'a>(v: &'a Value, k: &str) -> &'a str { v[k].as_str().unwrap_or("") }
fn arr<'a>(v: &'a Value, k: &str) -> &'a Vec<Value> { static EMPTY: Vec<Value> = Vec::new(); v[k].as_array().unwrap_or(&EMPTY) }
fn verdict(b: bool) -> &'static str { if b { "ACCEPT" } else { "REFUSE" } }

fn vk(pk: &[u8]) -> Option<VerifyingKey<P>> { VerifyingKey::<P>::try_from(pk).ok() }
fn sig(b: &[u8]) -> Option<Signature<P>> { Signature::<P>::try_from(b).ok() }
/// FIPS 205 slh_verify (Algorithm 24): pure interface, M' = 0x00 || len(ctx) || ctx || M. A signature that does not
/// parse (wrong length) is REFUSE, as the script's length guard and BouncyCastle's decoder make it.
fn verify_pure(pk: &[u8], msg: &[u8], ctx: &[u8], sigb: &[u8]) -> bool {
    match (vk(pk), sig(sigb)) { (Some(k), Some(sg)) => k.try_verify_with_context(msg, ctx, &sg).is_ok(), _ => false }
}
/// FIPS 205 slh_verify_internal (Algorithm 20) on an already-framed M'.
fn verify_internal(pk: &[u8], mprime: &[u8], sigb: &[u8]) -> bool {
    match (vk(pk), sig(sigb)) { (Some(k), Some(sg)) => k.slh_verify_internal(&[mprime], &sg).is_ok(), _ => false }
}

/// HashSLH-DSA framing (FIPS 205 Algorithm 23, section 10.2.2): M' = 0x01 || len(ctx) || ctx || OID || PH(M). The crate
/// has no pre-hash API, so the framing is built here and signed or verified through the internal interface; the
/// deterministic sigGen vectors check the OID bytes byte for byte.
fn prehash_mprime(hash_alg: &str, ctx: &[u8], m: &[u8]) -> Option<Vec<u8>> {
    use sha2::Digest;
    use sha3::digest::{ExtendableOutput, Update, XofReader};
    fn shake<H: Default + Update + ExtendableOutput>(m: &[u8], n: usize) -> Vec<u8> {
        let mut h = H::default(); h.update(m); let mut r = h.finalize_xof(); let mut o = vec![0u8; n]; r.read(&mut o); o
    }
    let (oid_last, ph): (u8, Vec<u8>) = match hash_alg {
        "SHA2-224" => (0x04, sha2::Sha224::digest(m).to_vec()),
        "SHA2-256" => (0x01, sha2::Sha256::digest(m).to_vec()),
        "SHA2-384" => (0x02, sha2::Sha384::digest(m).to_vec()),
        "SHA2-512" => (0x03, sha2::Sha512::digest(m).to_vec()),
        "SHA2-512/224" => (0x05, sha2::Sha512_224::digest(m).to_vec()),
        "SHA2-512/256" => (0x06, sha2::Sha512_256::digest(m).to_vec()),
        "SHA3-224" => (0x07, sha3::Sha3_224::digest(m).to_vec()),
        "SHA3-256" => (0x08, sha3::Sha3_256::digest(m).to_vec()),
        "SHA3-384" => (0x09, sha3::Sha3_384::digest(m).to_vec()),
        "SHA3-512" => (0x0a, sha3::Sha3_512::digest(m).to_vec()),
        "SHAKE-128" => (0x0b, shake::<sha3::Shake128>(m, 32)),
        "SHAKE-256" => (0x0c, shake::<sha3::Shake256>(m, 64)),
        _ => return None,
    };
    let mut out = vec![0x01u8, u8::try_from(ctx.len()).ok()?];
    out.extend_from_slice(ctx);
    out.extend_from_slice(&[0x06, 0x09, 0x60, 0x86, 0x48, 0x01, 0x65, 0x03, 0x04, 0x02, oid_last]);
    out.extend_from_slice(&ph);
    Some(out)
}

struct Tally { total: u32, fails: u32 }
impl Tally { fn check(&mut self, name: String, cond: bool, detail: String) { self.total += 1; if !cond { self.fails += 1; println!("FAIL {name} {detail}"); } } }

/// kat.ts's checks, same printed shape. Pre-hash groups are not skipped: the framing above covers every hashAlg.
fn kat(dir: &str) {
    let mut t = Tally { total: 0, fails: 0 };
    let groups = |f: &str| -> Vec<Value> { arr(&read_json(&format!("{dir}/{f}-internalProjection.json")), "testGroups").iter().filter(|g| s(g, "parameterSet") == PS).cloned().collect() };
    for g in groups("keyGen") {
        let mut n = 0;
        for tc in arr(&g, "tests") {
            let k = SigningKey::<P>::slh_keygen_internal(&unhex(s(tc, "skSeed")), &unhex(s(tc, "skPrf")), &unhex(s(tc, "pkSeed")));
            let vkey: &VerifyingKey<P> = k.as_ref();
            t.check(format!("keyGen tc{} pk", tc["tcId"]), vkey.to_vec() == unhex(s(tc, "pk")), String::new());
            t.check(format!("keyGen tc{} sk", tc["tcId"]), k.to_vec() == unhex(s(tc, "sk")), String::new());
            n += 1;
        }
        println!("kat keyGen tg{} {PS} tests={n}", g["tgId"]);
    }
    for g in groups("sigGen") {
        let (iface, pre) = (s(&g, "signatureInterface"), s(&g, "preHash")); let det = g["deterministic"].as_bool().unwrap_or(true);
        let mut n = 0;
        for tc in arr(&g, "tests") {
            let sk = SigningKey::<P>::try_from(unhex(s(tc, "sk")).as_slice()).expect("sk length");
            let (msg, ctx) = (unhex(s(tc, "message")), unhex(s(tc, "context")));
            let rnd = unhex(s(tc, "additionalRandomness"));
            if !det && rnd.len() != 16 { t.check(format!("sigGen tg{} tc{}", g["tgId"], tc["tcId"]), false, "randomized case without 16-byte additionalRandomness".into()); continue; }
            let opt_rand = if det { None } else { Some(rnd.as_slice()) };
            let sg = if iface == "internal" { sk.slh_sign_internal(&[&msg], opt_rand) }
                else if pre == "preHash" { let mp = prehash_mprime(s(tc, "hashAlg"), &ctx, &msg).expect("hashAlg"); sk.slh_sign_internal(&[&mp], opt_rand) }
                else { sk.try_sign_with_context(&msg, &ctx, opt_rand).expect("context length") };
            t.check(format!("sigGen tg{} tc{}", g["tgId"], tc["tcId"]), sg.to_vec() == unhex(s(tc, "signature")), format!("{iface}/{pre}/{}", s(tc, "hashAlg")));
            n += 1;
        }
        println!("kat sigGen tg{} {PS} {iface}/{pre} deterministic={det} tests={n}", g["tgId"]);
    }
    for g in groups("sigVer") {
        let (iface, pre) = (s(&g, "signatureInterface"), s(&g, "preHash"));
        let (mut n, mut neg) = (0, 0);
        for tc in arr(&g, "tests") {
            let (pk, msg, ctx, sgb) = (unhex(s(tc, "pk")), unhex(s(tc, "message")), unhex(s(tc, "context")), unhex(s(tc, "signature")));
            let expected = tc["testPassed"].as_bool().unwrap_or(false);
            let ok = if iface == "internal" { verify_internal(&pk, &msg, &sgb) }
                else if pre == "preHash" { let mp = prehash_mprime(s(tc, "hashAlg"), &ctx, &msg).expect("hashAlg"); verify_internal(&pk, &mp, &sgb) }
                else { verify_pure(&pk, &msg, &ctx, &sgb) };
            t.check(format!("sigVer tg{} tc{}", g["tgId"], tc["tcId"]), ok == expected, format!("expected {expected} ({})", s(tc, "reason")));
            n += 1; if !expected { neg += 1; }
        }
        println!("kat sigVer tg{} {PS} {iface}/{pre} tests={n} negatives={neg}", g["tgId"]);
    }
    println!("kat rust slh-dsa {} {PS}: checks={} failures={} {}", CRATE_VERSION, t.total, t.fails, if t.fails == 0 { "ALL PASS" } else { "FAILED" });
    if t.fails != 0 { process::exit(1); }
}

/// The harness's `acvp` input ({"cases": [{name, pk, mprime, sig, expected}]}): M' already framed, judged by the internal interface.
fn acvp_cases(path: &str, out: &str) {
    let cases = read_json(path); let (mut n, mut agree) = (0, 0); let mut rows = Vec::new();
    for c in arr(&cases, "cases") {
        let expected = c["expected"].as_bool().unwrap_or(false);
        let ok = verify_internal(&unhex(s(c, "pk")), &unhex(s(c, "mprime")), &unhex(s(c, "sig")));
        n += 1; if ok == expected { agree += 1; }
        println!("acvp-rust {} expected={} rust={} agree={}", s(c, "name"), verdict(expected), verdict(ok), ok == expected);
        rows.push(json!({"name": s(c, "name"), "expected": expected, "rust": ok}));
    }
    rows.push(json!({"summary": true, "cases": n, "agree": agree}));
    write_json(out, &json!({"cases": rows}));
    println!("acvp-rust cases={n} agree={agree} all_agree={}", agree == n);
}

/// diff-sign.ts's job: sign every digest the harness wrote, deterministic except every fourth spend (i % 4 == 3) with
/// 16 bytes of fresh randomness; verify each signature once here. Output shape = diff-sign.ts's, for `verify-ext`.
fn sign(keys_path: &str, digests_path: &str, out: &str) {
    let keys = read_json(keys_path); let digests = read_json(digests_path);
    let sk_of = |pk: &str| -> Vec<u8> { arr(&keys, "keys").iter().find(|k| s(k, "pk") == pk).map(|k| unhex(s(k, "sk"))).unwrap_or_else(|| { eprintln!("no secret for {pk}"); process::exit(2) }) };
    let t0 = Instant::now(); let (mut n, mut self_ok) = (0, 0); let mut out_keys = Vec::new();
    for k in arr(&digests, "keys") {
        let pk_hex = s(k, "pk"); let pk = unhex(pk_hex);
        let sk = SigningKey::<P>::try_from(sk_of(pk_hex).as_slice()).expect("sk length");
        let mut spends = Vec::new();
        for sp in arr(k, "spends") {
            let i = sp["i"].as_u64().unwrap_or(0); let msg = unhex(s(sp, "msg"));
            let randomized = i % 4 == 3;
            let mut rnd = [0u8; 16]; if randomized { getrandom::fill(&mut rnd).expect("getrandom"); }
            let sg = sk.try_sign_with_context(&msg, &[], if randomized { Some(&rnd) } else { None }).expect("sign").to_vec();
            n += 1; if verify_pure(&pk, &msg, &[], &sg) { self_ok += 1; }
            spends.push(json!({"i": i, "msg": s(sp, "msg"), "sig": hx(&sg), "randomized": randomized}));
        }
        out_keys.push(json!({"pk": pk_hex, "spends": spends}));
    }
    write_json(out, &json!({"keys": out_keys}));
    println!("sign-rust signatures={n} rust_self_verify={self_ok} seconds={:.1} -> {out}", t0.elapsed().as_secs_f64());
}

/// verify-ext's judgment from the Rust side: every spend's signature and the copy with one byte flipped at
/// (i * 997 + n * 7919) % 7856, n counting spends across the file, the same position the harness flips.
fn verify(sigs_path: &str, out: &str) {
    let sigs = read_json(sigs_path); let (mut n, mut acc, mut fref) = (0usize, 0, 0); let mut rows = Vec::new();
    let t0 = Instant::now();
    for k in arr(&sigs, "keys") {
        let pk_hex = s(k, "pk"); let pk = unhex(pk_hex);
        for sp in arr(k, "spends") {
            let i = sp["i"].as_u64().unwrap_or(0) as usize; let msg = unhex(s(sp, "msg")); let sg = unhex(s(sp, "sig"));
            let ok = verify_pure(&pk, &msg, &[], &sg);
            let pos = (i * 997 + n * 7919) % SIG_LEN;
            let mut flipped = sg.clone(); if pos < flipped.len() { flipped[pos] ^= 1; }
            let fok = verify_pure(&pk, &msg, &[], &flipped);
            n += 1; if ok { acc += 1; } if !fok { fref += 1; }
            println!("verify-rust key={} i={i} rust={} flip_pos={pos} flip_rust={}", &pk_hex[..16.min(pk_hex.len())], verdict(ok), verdict(fok));
            rows.push(json!({"pk": pk_hex, "i": i, "rust": verdict(ok), "flip_pos": pos, "flip_rust": verdict(fok)}));
        }
    }
    rows.push(json!({"summary": true, "spends": n, "rust_accept": acc, "flip_rust_refuse": fref}));
    write_json(out, &json!({"spends": rows}));
    println!("verify-rust spends={n} rust_accept={acc} flip_rust_refuse={fref} seconds={:.1} all_as_expected={}", t0.elapsed().as_secs_f64(), acc == n && fref == n);
}

/// The `negatives` input judged from the Rust side, joined by row name with the harness's output (script and
/// BouncyCastle verdicts). Rows whose mutation is in the transaction, not the signature (the output-field
/// negatives, the reordered outputs, the added input and data input), have no signature-level reading and are listed.
fn negatives(path: &str, two_outputs_digest: &str, second_box_digest: &str, prior_path: &str, out: &str) {
    let neg = read_json(path); let prior = read_json(prior_path);
    let pk = unhex(s(&neg, "pk"));
    let spends = arr(&neg, "spends"); let a = &spends[0]; let msg_a = unhex(s(a, "msg")); let sig_a = unhex(s(a, "sig"));
    let prior_rows: Vec<&Value> = arr(&prior, "rows").iter().filter(|r| r["summary"].is_null()).collect();
    let prior_of = |name: &str| -> Option<&Value> { prior_rows.iter().find(|r| s(r, "name") == name).copied() };
    let (mut n, mut as_expected, mut script_agree, mut script_joined, mut bc_agree, mut bc_joined) = (0, 0, 0, 0, 0, 0);
    let mut rows = Vec::new(); let mut judged = std::collections::HashSet::new();
    let mut row = |name: &str, prior_name: &str, expected: &str, ok: bool| {
        let got = verdict(ok); n += 1; if got == expected { as_expected += 1; }
        let p = prior_of(prior_name); judged.insert(prior_name.to_string());
        let script = p.map(|r| s(r, "script").to_string()); let bc = p.and_then(|r| r["bc"].as_bool());
        if let Some(sc) = &script { script_joined += 1; if sc == got { script_agree += 1; } }
        if let Some(b) = bc { bc_joined += 1; if b == ok { bc_agree += 1; } }
        println!("negatives-rust {name} expected={expected} rust={got} script={} bc={}{}", script.clone().unwrap_or("-".into()), bc.map(verdict).unwrap_or("-"), if got == expected { "" } else { " UNEXPECTED" });
        rows.push(json!({"name": name, "expected": expected, "rust": got, "script": script, "bc": bc, "ok": got == expected}));
    };
    row("honest_A", "honest_A", "ACCEPT", verify_pure(&pk, &msg_a, &[], &sig_a));
    for nm in arr(&neg, "named") { let name = s(nm, "name"); row(name, name, s(nm, "expected"), verify_pure(&pk, &msg_a, &[], &unhex(s(nm, "sig")))); }
    if let Some(sg2) = neg["sig_two_outputs"].as_str() { row("two_outputs_honest", "two_outputs_honest", "ACCEPT", verify_pure(&pk, &unhex(two_outputs_digest), &[], &unhex(sg2))); }
    if let Some(sg2) = neg["sig_second_box"].as_str() { row("second_box_own_signature", "two_boxes_one_key", "ACCEPT", verify_pure(&pk, &unhex(second_box_digest), &[], &unhex(sg2))); }
    let not_judged: Vec<String> = prior_rows.iter().map(|r| s(r, "name").to_string()).filter(|nme| !judged.contains(nme)).collect();
    println!("negatives-rust transaction-level rows with no signature reading ({}): {}", not_judged.len(), not_judged.join(","));
    rows.push(json!({"summary": true, "rows": n, "as_expected": as_expected, "script_joined": script_joined, "script_agree": script_agree, "bc_joined": bc_joined, "bc_agree": bc_agree, "transaction_level_not_judged": not_judged}));
    write_json(out, &json!({"rows": rows}));
    println!("negatives-rust rows={n} as_expected={as_expected} script_joined={script_joined} script_agree={script_agree} bc_joined={bc_joined} bc_agree={bc_agree} all_as_expected={}", as_expected == n && script_agree == script_joined && bc_agree == bc_joined);
}

fn main() {
    let a: Vec<String> = std::env::args().skip(1).collect();
    let r: Vec<&str> = a.iter().map(String::as_str).collect();
    match r.as_slice() {
        ["kat", dir] => kat(dir),
        ["acvp-cases", path, out] => acvp_cases(path, out),
        ["sign", keys, digests, out] => sign(keys, digests, out),
        ["verify", sigs, out] => verify(sigs, out),
        ["negatives", path, d2, dsb, prior, out] => negatives(path, d2, dsb, prior, out),
        _ => { eprintln!("usage: slhdsa-rust-rig kat <acvp dir> | acvp-cases <cases.json> <out> | sign <keys.json> <digests.json> <out> | verify <sigs.json> <out> | negatives <neg.json> <two_outputs_digest> <second_box_digest> <prior-out.json> <out>"); process::exit(2) }
    }
}
