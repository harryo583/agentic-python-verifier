---- MODULE Accounts_Abs ----
EXTENDS Naturals

CONSTANTS Accts, Cap, Amounts

VARIABLES balances

vars == << balances >>

TypeOK == balances \in [Accts -> 0..Cap]

Init == balances = [a \in Accts |-> 5]

Debit(a, amt) ==
  /\ a \in Accts /\ amt \in Amounts
  /\ balances[a] >= amt
  /\ balances' = [balances EXCEPT ![a] = @ - amt]

Credit(a, amt) ==
  /\ a \in Accts /\ amt \in Amounts
  /\ balances[a] + amt <= Cap
  /\ balances' = [balances EXCEPT ![a] = @ + amt]

TransferStep ==
  \E from \in Accts, to \in Accts, amt \in Amounts:
    /\ from # to
    /\ balances[from] >= amt
    /\ balances[to] + amt <= Cap
    /\ balances' = [balances EXCEPT ![from] = @ - amt, ![to] = @ + amt]

Next == TransferStep

Spec == Init /\ [][Next]_vars

SumBal == balances["A"] + balances["B"]

Inv ==
  /\ TypeOK
  /\ SumBal = 10

Property == \A a \in Accts: balances[a] >= 0 /\ balances[a] <= Cap
====
