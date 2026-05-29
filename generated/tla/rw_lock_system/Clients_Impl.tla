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
          await \A o \in Clients : client_state[o] # "writing";
          client_state[c] := "reading";
        or
          await client_state[c] = "reading";
          client_state[c] := "idle";
        or
          await client_state[c] = "idle";
          await \A o \in Clients : client_state[o] = "idle";
          client_state[c] := "writing";
        or
          await client_state[c] = "writing";
          client_state[c] := "idle";
        end either;
      end with;
    end while;
end algorithm; *)
\* BEGIN TRANSLATION (chksum(pcal) = "cc66dc34" /\ chksum(tla) = "a692326c")
VARIABLE client_state

vars == << client_state >>

Init == (* Global variables *)
        /\ client_state = [c \in Clients |-> "idle"]

Next == \E c \in Clients:
          \/ /\ client_state[c] = "idle"
             /\ \A o \in Clients : client_state[o] # "writing"
             /\ client_state' = [client_state EXCEPT ![c] = "reading"]
          \/ /\ client_state[c] = "reading"
             /\ client_state' = [client_state EXCEPT ![c] = "idle"]
          \/ /\ client_state[c] = "idle"
             /\ \A o \in Clients : client_state[o] = "idle"
             /\ client_state' = [client_state EXCEPT ![c] = "writing"]
          \/ /\ client_state[c] = "writing"
             /\ client_state' = [client_state EXCEPT ![c] = "idle"]

Spec == Init /\ [][Next]_vars

\* END TRANSLATION 

WritersSet == { c \in Clients : client_state[c] = "writing" }
ReadersSet == { c \in Clients : client_state[c] = "reading" }

Inv ==
  /\ client_state \in [Clients -> {"idle","reading","writing"}]
  /\ Cardinality(WritersSet) <= 1
  /\ ~(ReadersSet # {} /\ WritersSet # {})

Property == Inv
====
