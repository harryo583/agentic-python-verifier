---- MODULE Clients_Impl ----
EXTENDS Naturals, FiniteSets

CONSTANTS Clients

(* --algorithm Clients
variables client_state = [c \in Clients |-> "idle"];
begin
  Loop:
    while TRUE do
      with c \in Clients do
        either
          await client_state[c] = "idle";
          client_state[c] := "reading";
        or
          await client_state[c] = "reading";
          client_state[c] := "idle";
        or
          await client_state[c] = "idle";
          await { x \in Clients : client_state[x] = "writing" } = {};
          client_state[c] := "writing";
        or
          await client_state[c] = "writing";
          client_state[c] := "idle";
        end either;
      end with;
    end while;
  Finish:
    skip;
end algorithm; *)
\* BEGIN TRANSLATION (chksum(pcal) = "8d371397" /\ chksum(tla) = "68403f8a")
VARIABLES client_state, pc

vars == << client_state, pc >>

Init == (* Global variables *)
        /\ client_state = [c \in Clients |-> "idle"]
        /\ pc = "Loop"

Loop == /\ pc = "Loop"
        /\ \E c \in Clients:
             \/ /\ client_state[c] = "idle"
                /\ client_state' = [client_state EXCEPT ![c] = "reading"]
             \/ /\ client_state[c] = "reading"
                /\ client_state' = [client_state EXCEPT ![c] = "idle"]
             \/ /\ client_state[c] = "idle"
                /\ { x \in Clients : client_state[x] = "writing" } = {}
                /\ client_state' = [client_state EXCEPT ![c] = "writing"]
             \/ /\ client_state[c] = "writing"
                /\ client_state' = [client_state EXCEPT ![c] = "idle"]
        /\ pc' = "Loop"

Finish == /\ pc = "Finish"
          /\ TRUE
          /\ pc' = "Done"
          /\ UNCHANGED client_state

(* Allow infinite stuttering to prevent deadlock on termination. *)
Terminating == pc = "Done" /\ UNCHANGED vars

Next == Loop \/ Finish
           \/ Terminating

Spec == Init /\ [][Next]_vars

Termination == <>(pc = "Done")

\* END TRANSLATION 

WritingSet == { c \in Clients : client_state[c] = "writing" }

Inv ==
  /\ client_state \in [Clients -> {"idle", "reading", "writing"}]
  /\ Cardinality(WritingSet) <= 1
  /\ pc \in {"Loop", "Finish", "Done"}

Property == Inv
====
