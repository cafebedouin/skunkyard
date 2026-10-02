// SK-026: verification cost of post-quantum signatures against the proveDlog leaf, on the node's own jar.
// Baseline replicates sigmastate DLogProver.computeCommitment (DLogProtocol.scala): a = g^z * (h^e)^-1 via the
// same dlogGroup methods the interpreter calls. PQ verifiers are Bouncy Castle's, from the same jar.
import java.math.BigInteger;
import java.security.SecureRandom;
import java.util.Arrays;
import org.bouncycastle.crypto.AsymmetricCipherKeyPair;
import org.bouncycastle.crypto.params.ParametersWithRandom;
import org.bouncycastle.pqc.crypto.mldsa.*;
import org.bouncycastle.pqc.crypto.falcon.*;
import org.bouncycastle.pqc.crypto.slhdsa.*;

public class Bench {
  static final int WARM = Integer.getInteger("warm", 2000), N = Integer.getInteger("n", 5000);
  static final SecureRandom rnd = new SecureRandom();
  static final byte[] msg = new byte[300]; // about a 1-in/2-out transaction's bytes-to-sign

  interface Op { boolean run(); }

  static void report(String name, Op op) {
    long[] t = new long[N];
    boolean ok = true;
    for (int i = 0; i < WARM; i++) ok &= op.run();
    for (int i = 0; i < N; i++) { long a = System.nanoTime(); ok &= op.run(); t[i] = System.nanoTime() - a; }
    Arrays.sort(t);
    double mean = 0; for (long x : t) mean += x; mean /= N;
    System.out.printf("%-34s ok=%b  median %8.1f us  p95 %8.1f us  mean %8.1f us  (n=%d, warm=%d)%n",
        name, ok, t[N/2]/1e3, t[(int)(N*0.95)]/1e3, mean/1e3, N, WARM);
  }

  public static void main(String[] a) throws Exception {
    rnd.nextBytes(msg);
    try {
      System.out.println("BouncyCastle: " + new org.bouncycastle.jce.provider.BouncyCastleProvider().getInfo());
    } catch (Throwable e) { System.out.println("BouncyCastle: version call failed: " + e); }
    System.out.println("Java: " + System.getProperty("java.version") + "  cores: " + Runtime.getRuntime().availableProcessors());

    // --- baseline: sigmastate's secp256k1 group, exactly computeCommitment's three calls
    final sigma.crypto.BcDlogGroup G = sigma.crypto.CryptoConstants$.MODULE$.dlogGroup();
    final sigma.crypto.Platform.Ecp g = G.generator();
    final BigInteger q = G.order();
    final BigInteger w = new BigInteger(256, rnd).mod(q);
    final sigma.crypto.Platform.Ecp h = G.exponentiate(g, w);
    final BigInteger z = new BigInteger(256, rnd).mod(q);
    final byte[] eBytes = new byte[24]; rnd.nextBytes(eBytes);
    final BigInteger e = new BigInteger(1, eBytes);
    report("proveDlog computeCommitment (sigma)", () -> {
      sigma.crypto.Platform.Ecp c = G.multiplyGroupElements(G.exponentiate(g, z), G.inverseOf(G.exponentiate(h, e)));
      return c != null;
    });
    report("  one exponentiate g^z (sigma)", () -> G.exponentiate(g, z) != null);

    // --- ML-DSA (FIPS 204)
    for (MLDSAParameters p : new MLDSAParameters[]{MLDSAParameters.ml_dsa_44, MLDSAParameters.ml_dsa_65, MLDSAParameters.ml_dsa_87}) {
      MLDSAKeyPairGenerator kpg = new MLDSAKeyPairGenerator();
      kpg.init(new MLDSAKeyGenerationParameters(rnd, p));
      AsymmetricCipherKeyPair kp = kpg.generateKeyPair();
      MLDSASigner s = new MLDSASigner();
      s.init(true, new ParametersWithRandom(kp.getPrivate(), rnd));
      s.update(msg, 0, msg.length);
      final byte[] sig = s.generateSignature();
      final MLDSAPublicKeyParameters pub = (MLDSAPublicKeyParameters) kp.getPublic();
      System.out.printf("%s: pk %d B, sig %d B%n", p.getName(), pub.getEncoded().length, sig.length);
      report(p.getName() + " verify", () -> {
        MLDSASigner v = new MLDSASigner(); v.init(false, pub); v.update(msg, 0, msg.length); return v.verifySignature(sig);
      });
    }

    // --- Falcon (FN-DSA draft)
    for (FalconParameters p : new FalconParameters[]{FalconParameters.falcon_512, FalconParameters.falcon_1024}) {
      FalconKeyPairGenerator kpg = new FalconKeyPairGenerator();
      kpg.init(new FalconKeyGenerationParameters(rnd, p));
      AsymmetricCipherKeyPair kp = kpg.generateKeyPair();
      FalconSigner s = new FalconSigner();
      s.init(true, new ParametersWithRandom(kp.getPrivate(), rnd));
      final byte[] sig = s.generateSignature(msg);
      final FalconPublicKeyParameters pub = (FalconPublicKeyParameters) kp.getPublic();
      System.out.printf("%s: pk %d B, sig %d B%n", p.getName(), pub.getH().length, sig.length);
      report(p.getName() + " verify", () -> { FalconSigner v = new FalconSigner(); v.init(false, pub); return v.verifySignature(msg, sig); });
    }

    // --- SLH-DSA (FIPS 205), the hash-based comparison
    for (SLHDSAParameters p : new SLHDSAParameters[]{SLHDSAParameters.sha2_128s, SLHDSAParameters.sha2_128f}) {
      SLHDSAKeyPairGenerator kpg = new SLHDSAKeyPairGenerator();
      kpg.init(new SLHDSAKeyGenerationParameters(rnd, p));
      AsymmetricCipherKeyPair kp = kpg.generateKeyPair();
      SLHDSASigner s = new SLHDSASigner();
      s.init(true, new ParametersWithRandom(kp.getPrivate(), rnd));
      final byte[] sig = s.generateSignature(msg);
      final SLHDSAPublicKeyParameters pub = (SLHDSAPublicKeyParameters) kp.getPublic();
      System.out.printf("%s: pk %d B, sig %d B%n", p.getName(), pub.getEncoded().length, sig.length);
      final int n = Integer.getInteger("slhN", 500);
      long[] t = new long[n]; boolean ok = true;
      for (int i = 0; i < 100; i++) { SLHDSASigner v = new SLHDSASigner(); v.init(false, pub); ok &= v.verifySignature(msg, sig); }
      for (int i = 0; i < n; i++) { long a0 = System.nanoTime(); SLHDSASigner v = new SLHDSASigner(); v.init(false, pub); ok &= v.verifySignature(msg, sig); t[i] = System.nanoTime()-a0; }
      Arrays.sort(t); double mean=0; for (long x: t) mean+=x; mean/=n;
      System.out.printf("%-34s ok=%b  median %8.1f us  p95 %8.1f us  mean %8.1f us  (n=%d, warm=100)%n", p.getName()+" verify", ok, t[n/2]/1e3, t[(int)(n*0.95)]/1e3, mean/1e3, n);
    }
  }
}
