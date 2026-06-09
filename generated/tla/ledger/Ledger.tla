---- MODULE Ledger ----
EXTENDS Naturals, Sequences, TLC

CONSTANTS Accts, Amounts, MaxLen, Cap

VARIABLES balances, log, pcA, pcL

vars == << balances, log, pcA, pcL >>

Acc == INSTANCE Accounts_Impl WITH balances <- balances, pc <- pcA
Log == INSTANCE AuditLog_Impl WITH log <- log, pc <- pcL

InitialBalances == [a \in Accts |-> 5]

SumBal == balances["A"] + balances["B"]

CreditedTo(x) ==
  LET F[i \in 0..Len(log)] ==
        IF i = 0 THEN 0
        ELSE F[i-1] + (IF log[i][2] = x THEN log[i][3] ELSE 0)
  IN F[Len(log)]

DebitedFrom(x) ==
  LET F[i \in 0..Len(log)] ==
        IF i = 0 THEN 0
        ELSE F[i-1] + (IF log[i][1] = x THEN log[i][3] ELSE 0)
  IN F[Len(log)]

AuditIntegrity ==
  \A x \in Accts : balances[x] - InitialBalances[x] = CreditedTo(x) - DebitedFrom(x)

BoundsOK == \A x \in Accts : balances[x] \in 0..Cap

Conservation == SumBal = 10

Init == Acc!Init /\ Log!Init

Next == Acc!Next /\ Log!Next

Spec == Init /\ [][Next]_vars

Inv == Acc!Inv /\ Log!Inv /\ BoundsOK /\ Conservation /\ AuditIntegrity

Property == Conservation /\ BoundsOK /\ AuditIntegrity
====
