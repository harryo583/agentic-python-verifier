---- MODULE Accounts_Impl ----
EXTENDS Naturals, TLC

CONSTANTS Accts, Cap, Amounts

(* --algorithm Accounts
variables balances = [a \in Accts |-> 5];
begin
  Loop:
    while TRUE do
      with from \in Accts, to \in Accts, amt \in Amounts do
        await from # to;
        await balances[from] >= amt;
        await balances[to] + amt <= Cap;
        balances := [balances EXCEPT ![from] = @ - amt, ![to] = @ + amt];
      end with;
    end while;
  Finish:
    skip;
end algorithm; *)
\* BEGIN TRANSLATION (chksum(pcal) = "a815adc0" /\ chksum(tla) = "fdb338b2")
VARIABLES balances, pc

vars == << balances, pc >>

Init == (* Global variables *)
        /\ balances = [a \in Accts |-> 5]
        /\ pc = "Loop"

Loop == /\ pc = "Loop"
        /\ \E from \in Accts:
             \E to \in Accts:
               \E amt \in Amounts:
                 /\ from # to
                 /\ balances[from] >= amt
                 /\ balances[to] + amt <= Cap
                 /\ balances' = [balances EXCEPT ![from] = @ - amt, ![to] = @ + amt]
        /\ pc' = "Loop"

Finish == /\ pc = "Finish"
          /\ TRUE
          /\ pc' = "Done"
          /\ UNCHANGED balances

(* Allow infinite stuttering to prevent deadlock on termination. *)
Terminating == pc = "Done" /\ UNCHANGED vars

Next == Loop \/ Finish
           \/ Terminating

Spec == Init /\ [][Next]_vars

Termination == <>(pc = "Done")

\* END TRANSLATION 

SumBal == balances["A"] + balances["B"]

TypeOK == balances \in [Accts -> 0..Cap]

Inv ==
  /\ TypeOK
  /\ SumBal = 10
  /\ pc \in {"Loop", "Finish", "Done"}

Property == \A a \in Accts: balances[a] >= 0 /\ balances[a] <= Cap
====
