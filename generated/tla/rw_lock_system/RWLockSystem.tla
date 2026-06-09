---- MODULE RWLockSystem ----
EXTENDS Naturals, FiniteSets

CONSTANTS Clients, MaxReaders

VARIABLES state, reader_count, client_state, pcL, pcC

vars == << state, reader_count, client_state, pcL, pcC >>
lockVars == << state, reader_count, pcL >>
clientVars == << client_state, pcC >>

L == INSTANCE RWLock_Impl WITH state <- state, reader_count <- reader_count, pc <- pcL
C == INSTANCE Clients_Impl WITH client_state <- client_state, pc <- pcC

Init == L!Init /\ C!Init

Next ==
  \/ (L!Next /\ UNCHANGED clientVars)
  \/ (C!Next /\ UNCHANGED lockVars)

Spec == Init /\ [][Next]_vars

ReadingClients == { c \in Clients : client_state[c] = "reading" }
WritingClients == { c \in Clients : client_state[c] = "writing" }

TypeOK ==
  /\ state \in {"free", "read", "write"}
  /\ reader_count \in 0..MaxReaders
  /\ client_state \in [Clients -> {"idle", "reading", "writing"}]

MutualExclusion ==
  (state = "write") => (reader_count = 0 /\ Cardinality(WritingClients) <= 1)

NoTornState ==
  /\ (\E c \in Clients : client_state[c] = "reading") => (state = "read" /\ reader_count >= 1)
  /\ (state = "free") => (reader_count = 0 /\ ReadingClients = {} /\ WritingClients = {})

CountAgrees == reader_count = Cardinality(ReadingClients)

Inv ==
  /\ TypeOK
  /\ MutualExclusion
  /\ NoTornState
  /\ CountAgrees

Property ==
  /\ MutualExclusion
  /\ NoTornState
  /\ CountAgrees

====
