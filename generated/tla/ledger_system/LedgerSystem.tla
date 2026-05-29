---- MODULE LedgerSystem ----
EXTENDS Naturals, Sequences, TLC

CONSTANTS Accts, Cap, Init0, Amounts, MaxLogLen

VARIABLES balances, log, pcA, pcL

Acc == INSTANCE Accounts_Impl WITH balances <- balances, pc <- pcA
Log == INSTANCE AuditLog_Impl WITH log <- log, pc <- pcL

vars == << balances, log, pcA, pcL >>

Entry == [from: Accts, to: Accts, amount: Amounts]

BoundedLog == UNION { [1..n -> Entry] : n \in 0..MaxLogLen }

TypeOK ==
  /\ balances \in [Accts -> 0..Cap]
  /\ log \in BoundedLog

InitTotal == 2 * Init0

SumBal == balances["A"] + balances["B"]

RECURSIVE NetFor(_, _)
NetFor(a, i) ==
  IF i = 0 THEN 0
  ELSE LET e == log[i] IN
       NetFor(a, i-1)
       + (IF e.to = a THEN e.amount ELSE 0)
       - (IF e.from = a THEN e.amount ELSE 0)

Net(a) == NetFor(a, Len(log))

Init ==
  /\ balances = [a \in Accts |-> Init0]
  /\ log = << >>
  /\ pcA = "Loop"
  /\ pcL = "Loop"

DoTransfer(f, t, amt) ==
  /\ f \in Accts /\ t \in Accts /\ f # t
  /\ amt \in Amounts
  /\ balances[f] >= amt
  /\ balances[t] + amt <= Cap
  /\ Len(log) < MaxLogLen
  /\ balances' = [balances EXCEPT ![f] = @ - amt, ![t] = @ + amt]
  /\ log' = Append(log, [from |-> f, to |-> t, amount |-> amt])
  /\ UNCHANGED << pcA, pcL >>

Stutter == UNCHANGED vars

Next ==
  \/ \E f, t \in Accts, amt \in Amounts : DoTransfer(f, t, amt)
  \/ Stutter

Spec == Init /\ [][Next]_vars

Inv ==
  /\ TypeOK
  /\ SumBal = InitTotal
  /\ \A a \in Accts : balances[a] = Init0 + Net(a)

Property ==
  /\ SumBal = InitTotal
  /\ \A a \in Accts : balances[a] >= 0 /\ balances[a] <= Cap

====
