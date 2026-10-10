{
  // How many headers does the context carry? Spendable by anyone only if CONTEXT.headers.size == N.
  // Compiled for N = 9 and N = 10.
  sigmaProp(CONTEXT.headers.size == $N)
}
