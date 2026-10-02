// skunks/oneshot/web/sigma.ts: the sigmastate-js bundle (docs/oneshot/oneshot-sigma.js), loaded by the page only
// when a P2SH spend is signed. It exposes the sigmastate-js/main module object as globalThis.oneshotSigma; all the
// spend logic stays in src/p2sh-spend.ts (in oneshot.js), which takes this object as an argument.
import * as S from 'sigmastate-js/main';

(globalThis as unknown as { oneshotSigma: unknown }).oneshotSigma = S;
