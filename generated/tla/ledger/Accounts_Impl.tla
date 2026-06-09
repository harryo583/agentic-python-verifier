---- MODULE Accounts_Impl ----
EXTENDS Naturals, TLC

CONSTANTS Accts, Amounts, Cap

(* --algorithm Accounts
variables balances = [a \in Accts |-> 5];
begin
  Loop:
    while TRUE do
      either
        with x \in Accts, n \in Amounts do
          await balances[x] >= n;
          balances[x] := balances[x] - n;
        end with;
      or
        with x \in Accts, n \in Amounts do
          await balances[x] + n <= Cap;
          balances[x] := balances[x] + n;
        end with;
      end either;
    end while;
  Finish:
    skip;
end algorithm; *)
\* BEGIN TRANSLATION (chksum(pcal) = "bf54560" /\ chksum(tla) = "d44fe63")
VARIABLES balances, pc

vars == << balances, pc >>

Init == (* Global variables *)
        /\ balances = [a \in Accts |-> 5]
        /\ pc = "Loop"

Loop == /\ pc = "Loop"
        /\ \/ /\ \E x \in Accts:
                   \E n \in Amounts:
                     /\ balances[x] >= n
                     /\ balances' = [balances EXCEPT ![x] = balances[x] - n]
           \/ /\ \E x \in Accts:
                   \E n \in Amounts:
                     /\ balances[x] + n <= Cap
                     /\ balances' = [balances EXCEPT ![x] = balances[x] + n]
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

Inv ==
  /\ balances \in [Accts -> 0..Cap]
  /\ pc \in {"Loop", "Finish", "Done"}

Property == Inv
====
