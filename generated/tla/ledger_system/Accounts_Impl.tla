---- MODULE Accounts_Impl ----
EXTENDS Naturals, TLC

CONSTANTS Accts, Cap, Init0, Amounts

(* --algorithm Accounts
variables balances = [a \in Accts |-> Init0];
begin
  Loop:
    while TRUE do
      with f \in Accts, t \in Accts, amt \in Amounts do
        await f # t;
        await balances[f] >= amt;
        await balances[t] + amt <= Cap;
        balances := [balances EXCEPT ![f] = @ - amt, ![t] = @ + amt];
      end with;
    end while;
  Finish:
    skip;
end algorithm; *)
\* BEGIN TRANSLATION (chksum(pcal) = "24063fb2" /\ chksum(tla) = "534da637")
VARIABLES balances, pc

vars == << balances, pc >>

Init == (* Global variables *)
        /\ balances = [a \in Accts |-> Init0]
        /\ pc = "Loop"

Loop == /\ pc = "Loop"
        /\ \E f \in Accts:
             \E t \in Accts:
               \E amt \in Amounts:
                 /\ f # t
                 /\ balances[f] >= amt
                 /\ balances[t] + amt <= Cap
                 /\ balances' = [balances EXCEPT ![f] = @ - amt, ![t] = @ + amt]
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

TypeOK == balances \in [Accts -> 0..Cap]

SumBal == balances["A"] + balances["B"]

Inv ==
  /\ TypeOK
  /\ SumBal = 2 * Init0
  /\ pc \in {"Loop", "Finish", "Done"}

Property == \A a \in Accts : balances[a] >= 0 /\ balances[a] <= Cap

====
