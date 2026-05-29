---- MODULE Accounts_Abs ----
EXTENDS Naturals

CONSTANTS Accts, Cap, Init0, Amounts

VARIABLES balances

vars == << balances >>

TypeOK == balances \in [Accts -> 0..Cap]

Init == balances = [a \in Accts |-> Init0]

DoXfer(f, t, amt) ==
  /\ f \in Accts /\ t \in Accts /\ f # t
  /\ amt \in Amounts
  /\ balances[f] >= amt
  /\ balances[t] + amt <= Cap
  /\ balances' = [balances EXCEPT ![f] = @ - amt, ![t] = @ + amt]

Next ==
  \/ \E f, t \in Accts, amt \in Amounts : DoXfer(f, t, amt)
  \/ UNCHANGED vars

Spec == Init /\ [][Next]_vars

SumBal == balances["A"] + balances["B"]

Inv == TypeOK /\ SumBal = 2 * Init0

Property == \A a \in Accts : balances[a] >= 0 /\ balances[a] <= Cap

====
