---- MODULE LedgerSystem ----
EXTENDS Naturals, Sequences, TLC

CONSTANTS Accts, Cap, Amounts, MaxLogLen

VARIABLES balances, log, pcAcc, pcLog

InitBal == [a \in Accts |-> 5]

Acc == INSTANCE Accounts_Impl WITH balances <- balances, pc <- pcAcc, Accts <- Accts, Cap <- Cap, Amounts <- Amounts
Log == INSTANCE AuditLog_Impl  WITH log <- log,           pc <- pcLog, Accts <- Accts, Amounts <- Amounts, MaxLogLen <- MaxLogLen

vars == << balances, log, pcAcc, pcLog >>

EntryT == [from: Accts, to: Accts, amount: Amounts]

TypeOK ==
  /\ balances \in [Accts -> 0..Cap]
  /\ log \in UNION { [1..n -> EntryT] : n \in 0..MaxLogLen }
  /\ pcAcc \in {"Loop", "Finish", "Done"}
  /\ pcLog \in {"Loop", "Finish", "Done"}

SumBalances == balances["A"] + balances["B"]

RECURSIVE CreditsTo(_, _)
CreditsTo(s, a) ==
  IF Len(s) = 0 THEN 0
  ELSE (IF s[1].to = a THEN s[1].amount ELSE 0) + CreditsTo(Tail(s), a)

RECURSIVE DebitsFrom(_, _)
DebitsFrom(s, a) ==
  IF Len(s) = 0 THEN 0
  ELSE (IF s[1].from = a THEN s[1].amount ELSE 0) + DebitsFrom(Tail(s), a)

Init ==
  /\ balances = [a \in Accts |-> 5]
  /\ log = << >>
  /\ pcAcc = "Loop"
  /\ pcLog = "Loop"

Transfer(from, to, amount) ==
  /\ from \in Accts /\ to \in Accts /\ from # to
  /\ amount \in Amounts
  /\ balances[from] >= amount
  /\ balances[to] + amount <= Cap
  /\ Len(log) < MaxLogLen
  /\ balances' = [balances EXCEPT ![from] = @ - amount, ![to] = @ + amount]
  /\ log' = Append(log, [from |-> from, to |-> to, amount |-> amount])
  /\ UNCHANGED << pcAcc, pcLog >>

Next ==
  \E from \in Accts, to \in Accts, amount \in Amounts:
    Transfer(from, to, amount)

Spec == Init /\ [][Next]_vars

AuditIntegrity ==
  \A a \in Accts:
    InitBal[a] + CreditsTo(log, a) - DebitsFrom(log, a) = balances[a]

Inv ==
  /\ TypeOK
  /\ SumBalances = 10
  /\ \A a \in Accts: balances[a] \in 0..Cap
  /\ AuditIntegrity

Property ==
  /\ SumBalances = 10
  /\ \A a \in Accts: balances[a] >= 0 /\ balances[a] <= Cap
  /\ AuditIntegrity

====
