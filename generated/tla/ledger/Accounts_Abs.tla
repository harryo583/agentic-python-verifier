---- MODULE Accounts_Abs ----
EXTENDS Naturals

CONSTANTS Accts, Amounts, Cap

VARIABLES balances

vars == << balances >>

Init == balances = [a \in Accts |-> 5]

Debit(x, n) ==
  /\ x \in Accts
  /\ n \in Amounts
  /\ balances[x] >= n
  /\ balances' = [balances EXCEPT ![x] = @ - n]

Credit(x, n) ==
  /\ x \in Accts
  /\ n \in Amounts
  /\ balances[x] + n <= Cap
  /\ balances' = [balances EXCEPT ![x] = @ + n]

Next ==
  \/ \E x \in Accts, n \in Amounts : Debit(x, n)
  \/ \E x \in Accts, n \in Amounts : Credit(x, n)
  \/ UNCHANGED balances

Spec == Init /\ [][Next]_vars

Inv ==
  /\ balances \in [Accts -> 0..Cap]

Property == Inv
====
