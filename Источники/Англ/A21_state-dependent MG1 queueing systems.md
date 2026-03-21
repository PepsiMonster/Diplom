

State-DependentM/G/1 Queueing Systems
Hossein Abouee-Mehrizi
Department of Management Sciences, University of Waterloo, Waterloo, ON, N2L 3G1, CANADA,
HAboueeMehrizi@UWaterloo.ca
## Opher Baron
Joseph L. Rotman School of Management, University of Toronto, Toronto, M5S 3E6, CANADA,
Opher.Baron@Rotman.Utoronto.Ca
We consider a state-dependentM
n
## /G
n
/1 queueing system with both finite and infinite buffer sizes. We allow
the arrival rate of customers to depend on the number of people in the system. Service times are also state-
dependent and service rates can be modified at both arrivals and departures of customers. We show that
the steady-state solution of this system at arbitrary times can be derived using the supplementary variable
method, and that the system’s state at arrival epochs can be analyzed using an embedded Markov chain.
For the system with infinite buffer size, we first obtain an expression for the steady-state distribution of the
number of customers in the system at both arbitrary and arrival times. Then, we derive the average service
time of a customer observed at both arbitrary times and arrival epochs. We show that our state-dependent
queueing system is equivalent to a Markovian birth-and-death process. This equivalency demonstrates our
main insight that theM
n
## /G
n
/1 system can be decomposed at any given state as a Markovian queue. Thus,
many of the existing results for systems modeled asM/M/1 queue can be carried through to the much more
practicalM/G/1 model with state-dependent arrival and service rates. Then, we extend the results to the
## M
n
## /G
n
/1 queueing systems with finite buffer size.
Key words:M
n
## /G
n
/1 queue, birth-and-death process, state-dependent service times, state-dependent
arrivals
## 1.  Introduction
Markovian  queues  have  been  used  to  model  and  analyze  congested  queueing  systems  in  a  vast
body  of  literature.  The  beauty  of  the  single  stage  Markovian  queues  is  that  the  system  can  be
modeled as a Birth-and-Death (B&D) process and decomposed to new Markovian queues at any
given state. These properties make the problem tractable even when the arrivals and service rates
are state-dependent or when the control of the queue dynamically changes. This tractability made
theM/M/1 queue a preferable model for many theoretical studies in management science.
However, in many applications assuming Markovian service times is not realistic. Thus, much
attention has been given to analysis of queues with generally distributed service times. An impor-
tant limitation of such queueing systems however is that their analysis is not straightforward. This
## 1

## 2
limitation is especially true when the arrival rates and the service times depend on the state of the
system. Moreover, sinceM/G/1 systems are not regenerative at arrival epochs, the solution of the
system is not simple when the control of the queue is adjusted at arrival epochs. This apparent
difficulty in the analysis of such queueing systems limited their study, even when they are more
appropriate for the application considered.
In  this  paper  we  consider  a  queueing  system  with  state-dependent  arrival  and  service  rates,
denoted asM
n
## /G
n
/1 with infinite and finite buffer sizes. Since the arrival process depends on the
number  of  customers  in  the  system,  the  Poisson  Arrival  Sees  Time  Average  (PASTA)  property
does not hold. Therefore, we consider the system in both continuous time and at arrival epochs.
To analyze the system in continuous time, we use the supplementary variable method to model
the system as a continuous time Markov Chain (MC). Using this method, we derive a closed form
expression for the steady-state distribution of the number of customers in the system (assuming,
of course, that the system is stable). Then, we obtain the steady-state rate at which theM
n
## /G
n
## /1
system moves from statento staten−1. These transition rates can be used to decompose the
state-dependent queueing systems as a B&D process, i.e., show that theM
n
## /G
n
/1 system can be
decomposed into severalM
n
## /G
n
/1 queues.
We  also  analyze  the  system  at  arrival  epochs.  We  define  an  embedded  MC  and  obtain  the
transition probabilities in these MCs. Then, we derive the steady-state distribution of the number
of  customers  in  the  systems  observed  by  an  arrival.  We  show  that  the  probability  of  havingn
customers  in  the  system  at  an  arbitrary  time  and  the  probability  of  observingnpeople  in  the
system by an arrival are closely related. Specifically, the ratio between these two distributions is
identical to the ratio of the arrival rate when there are no customers in the system to the arrival
rate when there arencustomers in the system. We also derive the steady-state service rate of a
customer in theM
n
## /G
n
/1 system observed at arrival epochs.
Using these results, we finally analyze theM
n
## /G
n
/1 state-dependent queueing systems with finite
buffer size and obtain the steady-state distribution of the number of people in both continuous
time and at arrival epochs.
The rest of the paper is organized as follows. In Section 2 we briefly review the related literature.
In Section 3 we define the problem and discuss some preliminary results. In Section 4 we model and
analyze theM
n
## /G
n
/1 system at both arbitrary times and arrival epochs. We extend the results to
## M
n
## /G
n
/1/Kin Section 5. We summarize the paper in Section 6. All proofs not in the body of the
paper appear in the Appendix.

## 3
## 2.  Literature Review
In  classical  single  server  queueing  systems  it  is  assumed  that  customers  who  are  looking  for  a
particular  service  arrive  to  the  system  according  to  a  stochastic  process  and  service  times  are
uncertain. One of the main assumptions in this literature is that the arrival and service rates are
constants and do not depend on the state of the system (see e.g., Kleinrock, 1975, Cohen, 1982,
Asmussen, 1991, Tijms, 2003, Gross and Harris, 2011).
Queueing systems with state-dependent arrival and service rates have been studied in the liter-
ature since Harris (1967). He provides the probability distribution of the number of people in the
system forM/M
n
/1 queueing systems where the rate of the service isμ
n
=nμ. He also derives the
probability distribution of the number of people in two-stateM/M/1 systems where the service
time of a customer depends on whether there are any other customers in the system or not at the
onset of their service. Shanthikumar (1979) considers a two-state state-dependentM/G/1 queueing
system and obtains the Laplace Transform (LT) of the steady-state waiting time distribution in
such a system. Regterschot and De Smit (1986) analyze anM/G/1 queueing system with Markov
modulated arrivals and service times. Gupta and Rao (1998) consider a queueing system with finite
buffer where the arrival rates and service times depend on the number of people in the system.
They assume that the service times can be adjusted only at the beginning of the service and obtain
the distribution of the number of people in the system in continuous time and at arrival epochs.
Kerner (2008) considers a state-dependentM
n
/G/1 queueing system and provides a closed form
expression  for  the  probability  distribution  of  the  number  of  people  in  the  system  as  a  function
of the probability that the server is idle. But in contrast to our results, he could not derive this
probability and doesn’t allow state-dependent service times. The derivations in both Gupta and
Rao (1998) and Kerner (2008) are special restrictive cases of our results.
Workload-dependent  queueing  systems  in  which  the  arrivals  and  service  times  depend  on  the
workload of the system rather than the number of people in the system have been also studied
in the literature since early 1960’s (see e.g., Gaver and Miller 1962). For example, Bekker et al.
(2004) consider a work-load dependent queueing system where both arrival rate and service speed
depend on the workload of the system. Assuming that the ratio of arrival rate and service speed is
equal in anM/G/1 system, they derive the steady-state distribution of the workload. Bekker and
Boxma (2007) consider anM/G/1 system where the service speed only changes at discrete points
of arrivals. Considering the case of an N-step service speed function, they obtain the distribution of
the workload right after and right before arrival epochs. Bekker et al. (2011) derive the steady-state

## 4
waiting time distribution of Markovian systems in which the service speed depends on the waiting
time of the first customer in line.
Another stream of related literature is papers using the supplementary variable method to derive
the analytical results. For example, Hokstad (1975a) considers anM/G/1 system and obtains the
joint distribution of the number of customers present in the system and the residual service time
using the supplementary variable technique. Hokstad (1975b) extends his results to anG/M/m
system. (See Cohen, 1982, and Kerner, 2008, for more detail about this literature.)
-  State-Dependent Queueing System
In this section we first define the problem considered in this paper precisely and explain some pre-
liminaries of this state-dependent queueing system. Then, we present known results for Markovian
systems to highlight the parallelism between the results we obtain for theM
n
## /G
n
/1 and those for
theM
n
## /M
n
## /1.
3.1.  Problem Definition and Preliminaries
We study a single server queue with state-dependent arrival rates and service times. Customers
arrive to the system according to a Poisson process with a rateλ
n
when there arencustomers in
the system. The service times are also state-dependent. Specifically, when there arencustomers in
the system and a new service time starts, it is generally distributed with a mean 1/μ
n
, a density
functionb
n
(·), and Laplace Transform (LT)
## ̃
b
n
(·). We assume thatb
n
(·) is absolutely continuous.
The density functionb
n
(·) may be completely different thanb
n+1
(·), e.g.,b
n+1
(·) can be uniformly
distributed whileb
n
(·) is exponentially distributed.
We also allow the service rate to change when a new customer arrives to the system as follows:
when there aren≥1 customers in the system and a new arrival occurs, the rate of the service
changes by a factor ofα
n+1
>0. This will lead to a reduction in the residual service of the customer
in service by this factor. (Note that ifα
n+1
<1 the service rate decreases and the residual service
time actually increases.) Specifically, an arrival that seesncustomers in the system and a remaining
service time ofηfor the customer in service, causes the service rate to immediately change such
that the remaining service time becomes
η
α
n+1
(assuming no future arrivals before the end of the
current service, as such arrivals will again change the residual service time byα
n+2
). That is, if
the residual service time when a new customer arrives,η, has a densityf(η), the remaining service
time after this arrival will change to
## 1
α
n+1
ηand therefore it will have a density of
## 1
α
n+1
f(
## 1
α
n+1
η).(1)

## 5
We assume that bothμ
n
andα
n
are finite and greater than zero, which implies that the means
of all service times are finite. We further assume a non-idling policy, i.e., the server starts working
as soon as there is a customer in the system and is only idle when the system is empty.
Assuming  the  system  detailed  above  is  stable,  letP(i)  denote  the  steady-state  probability  of
havingicustomers  in  the  system,  and
## 1
## ˆμ
i
denote  the  expected  service  time  given  there  arei
customers in the system. Note that expressing ˆμ
i
in our setting is not trivial because of the service
rate changes allowed. We will characterize it in Section 4. Moreover, assuming the system is stable
is equivalent to assuming that the utilization of the system is less than 1 or that the probability
that the server is idle,P(0), is greater than zero (e.g., Asmussen, 1991)
## P(0) = 1−
## ∞
## ∑
i=0
## P(i)
λ
i
## ˆμ
i+1
## >0.(2)
Condition (2) is based on the steady-state probabilitiesP(i) that require the stability condition
to be obtained. For theM
n
## /G
n
/1 system, we present the necessary and sufficient condition for the
stability of this system. A sufficient condition for the stability of this system is to have
λ
i
## ˆμ
i+1
<1 for
everyi≥CwhereCis a finite positive number (see e.g., Wang, 1994). The reason is that
λ
i
## ˆμ
i+1
## <1
ensures that the transient probability of being in stateCof the system is positive (since
## 1
## ˆμ
i
## <∞
and the arrival process is Poisson, the transit probability of being in any statei<Cis positive as
well).
Note that the PASTA property does not hold in theM
n
## /G
n
/1 system that we consider. The
reason is that the rate of the arrival process depends on the number of people in the system, so
future arrivals are not independent of the past and present states of the system. Therefore, the
Lack of Anticipation Assumption (LAA) required for PASTA does not hold in such systems (For
more detail on LAA and its essentiality to PASTA, see Medhi, 2002). However, conditioning on
the number of customers in the system, PASTA does hold. This property that is called conditional
PASTA (Van Doorn and Regterschot, 1988) will help us to analyze the systems at arrival epochs.
## 3.2.  Markovian Systems
To  highlight  the  parallelism  between  theM
n
## /G
n
/1  andM
n
## /M
n
/1  queues,  we  present  the  well
known analysis of the standardM
n
## /M
n
/1 queueing system in this section.
Suppose that customers arrive to the system according to a Poisson process with rateλ
j
when
there arejcustomers. Service times are exponentially distributed with a rateμ
j
whenever there
arejcustomers and letα
j
## =
μ
j
μ
j−1
. This queue can be modeled as a standard B&D process and
analyzed using the basic relation
λ
i
## P
## (
i
## )
## =μ
i+1
## P
## (
i+ 1
## )
i≥0,(3)

## 6
see e.g., Gross and Harris (2011), leading to:
Observation 1.Consider  theM
n
## /M
n
/1  system  with  arrival  rateλ
j
and  service  rateμ
j
when
there arejpeople in the system. Suppose that
## ∞
## ∑
i=1
λ
## 0
λ
i
i−1
## ∏
j=0
λ
j+1
μ
j+1
## <∞.(4)
Then, the steady-state distribution of the number of people in the system is
## P(i) =
λ
## 0
## P(0)
λ
i
i−1
## ∏
j=0
λ
j+1
μ
j+1
## ,(5)
where from (5) and the fact that
## ∑
## ∞
i=0
P(i) = 1, we obtain
## P(0) =
## 1
## 1 +
## ∑
## ∞
i=1
λ
## 0
λ
i
i−1
## ∏
j=0
λ
j+1
μ
j+1
## .(6)
Note  that  (3)  indicates  that  the  average  rate  of  moving  from  stateito  statei+ 1  while  the
process is in stateiis equal to the average rate of moving from statei+ 1 to stateiwhile the
process is in statei+ 1. This interpretation is sufficient to express the steady-state probabilities
## P
## (
i
## )
. Indeed from Level Crossing Theory (LCT) (Perry and Posner, 1990) for any stable system
that its states change by jumps of−1, 0, and 1, we have
average arrival rate while in state i∗P
## (
i
## )
=average service rate while in state i+ 1∗P
## (
i+ 1
## )
## .
## (7)
Equation (7) implies that the solution for any queueing system where service and arrivals happen
one at a time can be decomposed as in any B&D processes. Specifically, letλ
i
and  ˆμ
i
denote the
average arrival and service rates while the process is in statei, respectively. Then, (7) is equivalent
to (3) for theM
n
## /M
n
/1 system.
An important implication of the B&D representation for a Markovian queueing system is that
the system can be easily decomposed to new Markovian queues at any given state. This means
that the time periods in which there are at leastκpeople in the system can be modeled as an
## M
n
## /M
n
/1 queue with arrival rateλ
κ+i
and service rateμ
κ+i
(when there areicustomers in the
new system). We call thisM
n
## /M
n
/1 queue theAuxiliary queue. LetP
## A
(i) denote the steady-state
probability of havingipeople in the auxiliary queue. Let alsoF(i) :=
## ∑
i
j=0
## P(j). Then,
Observation 2.Queue Decomposition (QD) in Markovian systems:The  steady-state
probability of havingκ+i(i≥0) customers in the original queue and the steady-state probability
of havingi≥0 customers in the auxiliary queue are related as:
## P(κ+i) =
## (
1−F(κ−1)
## )
## P
## A
(i), i= 0,1,...(8)

## 7
We obtain a similar result for theM
n
## /G
n
/1 system in Section 4.1.3.
-  Analysis ofM
n
## /G
n
/1Queues
In this section, we first analyze the state-dependent queueing systems with general service time
distribution at both arbitrary times and arrival epochs. Then, we demonstrate that the number
of customers in theM
n
## /G
n
/1 system is identical in distribution to this number in a specific B&D
process and obtain the transition rates of this process.
## 4.1.  Time Average Analysis
To analyze theM
n
## /G
n
/1 system at an arbitrary time, we use the method of supplementary variable
introduced by Cox (1955), see also Chapter II.6 in Cohen (1982) and Hokstad (1975a). To model
the system using this method, we consider a pair of variablesn
t
andη
t
wheren
t
andη
t
denote
the number of customers in the system and the remaining service time of the customer in service,
respectively.  Note  thatη
t
is  called  the  supplementary  variable;  but  as  you  will  see  next,  it  has
an  important  role  in  characterizing  the  distribution  of  the  number  of  customers  in  the  system.
## Letp
n
(η,t) denote the probability-density of havingncustomers in the system when the residual
service time of the customer in service isηat timetso that:
p
## 0
(t) =P(n
t
## = 0),(9)
p
n
(η,t)dη=P(n
t
## =n)∩
## [
## (η <η
t
## ≤η+dη)
## ]
n= 1,2,3,...(10)
We have:
Theorem 1.The   Chapman-Kolmogorov   equations   that   describe   the   dynamic   of   the   pair
## {(n
t
## ,η
t
),t∈[0,∞)}in ourM
n
## /G
n
/1system are given by:
p
## 0
## (t+dt) =p
## 0
## (t)(1−λ
## 0
dt) +p
## 1
## (0,t)dt+o(dt).(11)
p
## 1
## (η−dt,t+dt) =p
## 1
## (η,t)(1−λ
## 1
dt) +p
## 2
## (0,t)b
## 1
## (η)dt+p
## 0
## (t)λ
## 0
b
## 1
## (η)dt+o(dt).(12)
p
j
## (η−dt,t+dt) =p
j
## (η,t)(1−λ
j
dt) +p
j+1
## (0,t)b
j
## (η)dt+α
j
p
j−1
## (
ηα
j
## ,t
## )
λ
j−1
dt+o(dt).
## (13)
## Proof.
Based on the definition of the supplementary variable that we use, we follow Hokstad (1975a) to
derive a set of relations for a small time interval (t,t+dt) considering the pair{(n
t
## ,η
t
## ),t∈[0,∞)}.
First, considerp
## 0
(t+dt): Note that the continuous time MC for state 0 is identical to the one
in theM/G/1 systems (the system is idle in both cases) and is given in Hokstad (1975a) as (11).

## 8
Next consider state (1,η−dt): If at timet+dtthe system is in state (1,η−dt) whereη−dt≥0,
at timetone of the following has happened: 1) the system was in state (1,η) and no new customer
arrived during the nextdtunits of time (with probability of 1−λ
## 1
dt+o(dt)); 2) the system was
in state (2,0) and the service time of the next customer to enter service wasη(with probability
ofb
## 1
(η)dt); 3) the system was in state (0) and a new customer arrived during the nextdtunits of
time (with probability ofλ
## 0
dt+o(dt)); or 4) other possible events with probabilityo(dt) or lower.
## Therefore,
p
## 1
## (η−dt,t+dt) =p
## 1
## (η,t)
## (
## 1−λ
## 1
dt+o(dt)
## )
## +p
## 2
## (0,t)b
## 1
## (η)dt+p
## 0
## (t)
## (
λ
## 0
dt+o(dt)
## )
b
## 1
## (η) +o(dt).
Combining all terms with order ofdt
## 2
ino(dt), we get (12).
Finally consider state (j,η) forj >1: If at timet+dtthe system state is (j,η−dt), at timet
one of the following has happened: 1) the system was in state (j,η) and no new customer arrived
during the nextdtunits of time (with probability of 1−λ
j
dt+o(dt)); 2) the system was in state
(j+ 1,0)  and  the  service  time  of  the  next  customer  wasη(with  probability  ofb
j
(η)dt);  3)  the
system was in state (j−1,ηα
j
) and a new customer arrived during the nextdtunits of time (with
probability ofλ
j−1
dt+o(dt)); or 4) other possible events with probabilityo(dt) or lower. Thus,
p
j
## (η−dt,t+dt) =p
j
## (η,t)(1−λ
j
dt+o(dt)) +p
j+1
## (0,t)b
j
## (η)dt+α
j
p
j−1
## (
t,ηα
j
## ) (
λ
j−1
dt+o(dt)
## )
## +o(dt).
Note  that  sincep
j−1
## (
t,η
## )
is  a  probability  density  function,  the  coefficientα
j
inα
j
p
j−1
## (
t,ηα
j
## )
ensuresα
j
p
j−1
## (
t,ηα
j
## )
is also a probability density function. Combining all terms with order ofdt
## 2
ino(dt), we get (13).
The pair (n
t
## ,η
t
) is a vector valued Markov process that represents the state of the system at
any given timet∈[0,∞). Therefore, (11 -13) present a continuous time Markov Chain (MC) for
theM
n
## /G
n
/1 system.
Theorem  1  generalized  the  continuous  time  MC  for  theM
n
/G/1  from  Kerner  (2008)  to  the
## M
n
## /G
n
/1 system we consider.
4.1.1. Distribution of Number of People in the SystemUsing  the  MC  presented  in
Theorem  1,  we  derive  the  steady-state  distribution  of  the  number  of  people  in  the  correspond-
ingM
n
## /G
n
/1 system. LetP(i) denote the steady-state probability of havingicustomers in the
## M
n
## /G
n
/1 system. Also, let
## ̃
h
j
## (
## ·
## )
denote the LT of the steady-state residual service time given that
there arej≥0 customers in the system where
## ̃
h
## 0
## (·) =
## ̃
b
## 1
## (·). Assuming
## ̃
h
j
(·) are given and setting
μ
## 0
## =μ
## 1
## ,α
## 1
= 1,P(i) are derived in the following theorem.

## 9
Theorem 2.Suppose that
## ∞
## ∑
i=1
λ
## 0
λ
i
i−1
## ∏
j=0
## 1−
## ̃
h
j
## (
λ
j+1
α
j+1
## )
## ̃
b
j+1
## (λ
j+1
## )
## <∞.(14)
Then, the steady-state distribution of the number of people in anM
n
## /G
n
/1queue is
## P(i) =
λ
## 0
## P(0)
λ
i
i−1
## ∏
j=0
## 1−
## ̃
h
j
## (
λ
j+1
α
j+1
## )
## ̃
b
j+1
## (λ
j+1
## )
## ,(15)
where from (15) and
## ∑
## ∞
i=0
P(i) = 1, we have
## P(0) =
## 1
## 1 +
## ∑
## ∞
i=1
λ
## 0
λ
i
i−1
## ∏
j=0
## 1−
## ̃
h
j
## (
λ
j+1
α
j+1
## )
## ̃
b
j+1
## (λ
j+1
## )
## .(16)
Condition (14) guarantees that the steady-state probability of having no customers in the system,
P(0), is larger than zero; it is necessary and sufficient for the stability of ourM
n
## /G
n
/1 system.
We next obtain
## ̃
h
i
## (
## ·
## )
recursively assuming that the system is stable.
Theorem 3.Suppose that theM
n
## /G
n
/1system is stable. Then, the LT of the steady-state distri-
bution of the residual service time given that there areicustomers in the system can be calculated
recursively from:
## ̃
h
i
## (s) =
λ
i
s−λ
i
## [
## ̃
b
i
## (λ
i
## )
## 1−
## ̃
h
i−1
## (
s
α
i
## )
## 1−
## ̃
h
i−1
## (
λ
i
α
i
## )
## −
## ̃
b
i
## (s)]i≥1,(17)
where
## ̃
h
## 0
## (·) =
## ̃
b
## 1
## (·).
To characterize
## ̃
h
i
(·) we assume the system is stable. But, this condition in (14) is a function
of
## ̃
h
i
(·). To verify the stability condition, one should assume that
## ̃
h
i
(·) obtained in Theorem 3 are
well defined, calculate them recursively, and then check if (14) holds. If (14) holds, then the system
is stable and therefore
## ̃
h
i
(·) are well defined.
The calculation of the LT in (17) depends on the distribution of the service time. In general,
when the expected residual service time approaches zero, this calculation takes longer. For example,
for a system with deterministic service time, obtaining the probability of having a large number
of people in the system may require a higher accuracy of the software used and take longer (as
the residual service times approach zero) compare to calculating the probability of having a small
number of people in the system.

## 10
4.1.2.  Modeling theM
n
## /G
n
/1Queues as a Birth-and-Death ProcessLet  ˆμ
i
denote
the  steady-state  rate  at  which  the  system  moves  from  stateitoi−1  wheniis  the  number  of
customers in the system. In the following observation, we obtain this rate.
Observation 3.The  steady-state  number  of  customers  in  theM
n
## /G
n
/1  system  has  the  same
distribution as the steady-state number of customers in a B&DM
n
## /M
n
/1 process with arrival rate
λ
i
and service rate
## ˆμ
i
## =
λ
i
## ̃
b
i
## (
λ
i
## )
## 1−
## ̃
h
i−1
## (
λ
i
α
i
## )
## (18)
when there areipeople in the system.
Using Observation 3 we rewrite the stability condition (14) as
## ∞
## ∑
i=1
λ
## 0
λ
i
i−1
## ∏
j=0
λ
j+1
## ˆμ
j+1
## <∞,(19)
the probability that there areicustomers in the system as
## P(i) =
λ
## 0
## P(0)
λ
i
i−1
## ∏
j=0
λ
j+1
## ˆμ
j+1
## ,(20)
and the probability that theM
n
## /G
n
/1 system is idle as
## P(0) =
## 1
## 1 +
## ∑
## ∞
i=1
λ
## 0
λ
i
i−1
## ∏
j=0
λ
j+1
## ˆμ
j+1
## .(21)
Comparing (19-21) with (4-6) we observe that the stability condition and the distribution of the
number  of  people  in  theM
n
## /G
n
/1  has  the  same  structure  as  the  one  in  theM
n
## /M
n
## /1.  This
similarity indicates that the solution of theM
n
## /G
n
/1 can be decomposed as in any B&D processes.
The expressions in (19-21) generalize the ones in equation (12) of Kerner (2008) for theM
n
## /G/1
to theM
n
## /G
n
/1 queueing system.
4.1.3. Queue Decomposition (QD) at a Given StateIn Observation 2, we showed that
theM
n
## /M
n
/1 queueing system can be decomposed at any given state. In this section we extend
this result to theM
n
## /G
n
/1 system. To decompose this system, as in Abouee-Mehrizi et al. (2012),
we define an auxiliary queue such that the steady-state probability of havingκ+icustomers in the
original system given that there areκor more people in this system is identical to the steady-sate
distribution of havingijobs in this auxiliary queue. To distinguish between the original queue and
the auxiliary queue, we use the term “job” in the auxiliary queue. We define the auxiliary queue
as anM
n
## /G
n
/1 queue with the following (a) arrival and (b) service processes:

## 11
Step (a):jobs arrive to the auxiliary queue according to a Poisson process with rateλ
κ+i
for
i≥0 when there areipeople in the auxiliary queue.
Step (b):the distribution of the first service time in each busy period of the auxiliary queue
is the distribution of the conditional residual service time in the original queue given that there
areκcustomers in the system, i.e., the equilibrium remaining service times given that there areκ
customers in the system. The distribution of the rest of the service times in each busy period of
the auxiliary queue is identical to the original queue, i.e.,b
κ+i
(·) fori≥0 when there areipeople
in the auxiliary queue. Moreover, when there areicustomers in the auxiliary queue and a new
arrival occurs, the rate of the service changes by a factor ofα
κ+i+1
## >0.
Since the auxiliary queue is anM
n
## /G
n
/1 queue, the steady-state distribution of the number of
jobs in this queue,P
## A
(i), can be obtained using Theorem 2 as:
## P
## A
(i) =P
## A
## (0)
i−1
## ∏
j=0
## 1−
## ̃
h
κ+j
## (λ
κ
## )
## ̃
b
κ
## (λ
κ
## )
## .(22)
Recall that in the originalM
n
## /G
n
/1 system we letF(i) :=
## ∑
i
j=0
## P(j). Then,
Observation 4.QD inM
n
## /G
n
/1systems:The steady-state probability of havingκ+i(i≥
0)  customers  in  the  originalM
n
## /G
n
/1  system  and  the  steady-state  probability  of  havingi≥0
customers in the auxiliary queue are related as:
## P(κ+i) =
## (
1−F(κ−1)
## )
## P
## A
(i), i= 0,1,...(23)
Observation  4  states  that  the  steady-state  number  of  jobs  in  the  auxiliary  queue  is  identical
to  the  steady-state  number  of  customers  in  the  original  state-dependent  queue  during  the  time
intervals when there are more thanκ−1 customers in the originalM
n
## /G
n
/1 system.
4.2.  Analysis at Arrival Epochs
In this section, we analyze theM
n
## /G
n
/1 at arrival epochs. We remind that since in this system
the arrival process is state-dependent, the PASTA property does not hold. Therefore, the steady-
state  distribution  of  the  number  of  customers  seen  by  an  arrival  is  typically  different  than  the
steady-state distribution of the number of customers in the system at an arbitrary time.
## Let
## ̄
## P
a
(n) denote the steady-state probability that anArrival observesncustomers in the system.
To obtain
## ̄
## P
a
(n), we recall that in theM
n
## /G
n
/1 the distribution of the number of customers seen
by  an  arrival  is  identical  to  the  steady-state  distribution  of  the  number  of  customers  seen  by  a
departure (this easily follows by a level crossing argument as in Buzacott and Shanthikumar, 1993).
Therefore, we analyze the system at departure epochs by defining an embedded MC.

## 12
LetM
n
denote the number of customers left behind by then
th
departing customer in the system.
## M
n
can  be  found  by  the  MC  embedded  at  theDepartures.  Let
## ̄
## P
d
(n)  denote  the  steady-state
distribution of being in statenof this MC. Then,
## ̄
## P
a
## (n) =
## ̄
## P
d
## (n).(24)
To derive
## ̄
## P
d
(n), we need to determine the one-step transition probabilities ofM
n
## ,
p
jk
## =P
## (
## M
n+1
=k|M
n
## =j
## )
## .(25)
For statej≥1, letv
j
k
denote the probability of havingk≥0 arrivals during the service time
that starts when there arejcustomers in the system. Forj= 0, the relevant service time starts
when there is one customer in the system. So we letv
## 0
k
## =v
## 1
k
. Then, the probability that the next
departure leaveskcustomers behind given that there are no customers in the system,p
## 0k
, isv
## 0
k
## .
Similarly, the probability that the next departure leaveskcustomers behind given that there are
j≥1  customers  in  the  system,p
jk
,  isv
j
k−j+1
.  To  summarize,  we  denote  the  one-step  transition
probabilities ofM
n
, the embedded MC, as
p
jk
## =
## {
v
## 0
k
,   j= 0;
v
j
k−j+1
, j≥1.
## (26)
In the standardM/G/1, these probabilities can be easily obtained since the distribution of the
service times is identical for all customers. Letλand
## ̃
b(·) denote the arrival rate and the LT of the
service time distribution in the standardM/G/1, respectively. Then,v
j
k
is independent ofjand
the probability generating function ofv
k
## :=v
j
k
(j= 0,1,...) is (see e.g., Takagi 1991)
## V(z) =
## ∞
## ∑
k=0
v
k
z
k
## =
## ̃
b(λ(1−z)).(27)
To obtainv
j
k
in theM
n
## /G
n
/1 queue, we consider the probability of a new arrival during the
residual service time observed by any customer upon arrival. Fortunately, this distribution possesses
the conditional PASTA property:
Corollary 1.The  conditional  steady-state  distribution  of  the  residual  service  time  observed  by
arrivals that findjcustomers in the system is identical to the conditional steady-state distribution
of  the  residual  service  time  at  an  arbitrary  time  in  theM
n
## /G
n
/1system  that  also  observesj
customers in the system.

## 13
We  next  determine  the  transition  probabilities,p
jk
,  forj >0.  (The  derivation  forp
## 0k
is
similar  but  more  detailed  and  it  is  provided  in  the  proof  of  Theorem  4.)  Considerp
j,j−1
## =
## P
## (
## M
n+1
=j−1|M
n
## =j
## )
, the probability that the next departing customer leaves one less customer
behind given that the last departing customer left. This is equal to the probability of no arrival
during the next service time,
## ̃
b
j
## (λ
j
) (e.g., Conway 1967, page 171). Therefore,
p
j,j−1
## =
## ̃
b
j
## (λ
j
),  j≥1.(28)
With similar logic, the probability that the next departing customer leaveskcustomers behind
given that the last departing customer leftj≥1 customers behind,P
## (
## M
n+1
=k|M
n
## =j
## )
, is equal
to the probability ofk−j+ 1 arrivals during the next service time. This probability is equal to the
probability that a customer arrives after the next service time starts,
## (
## 1−
## ̃
b
j
## (λ
j
## )
## )
, and a customer
arrives during the remaining service time of all arrivals that seei < kcustomers in the system,
## (
## 1−
## ̃
h
i
## (
λ
i+1
α
i+1
## )
## )
, and no arrival during the remaining service time once there arekcustomers in the
system,
## ̃
h
k
## (
λ
k+1
α
k+1
## ):
p
jk
## =
## ̃
h
k
## (
λ
k+1
α
k+1
## )
## (
## 1−
## ̃
b
j
## (λ
j
## )
## )
k−1
## ∏
i=j
## (
## 1−
## ̃
h
i
## (
λ
i+1
α
i+1
## ))
,  j≥1,k≥j.(29)
Note that for theM/M/1 queue we have
## ̃
h
j
## (λ
j
## ) =
## ̃
b
i
## (λ
i
## ) =
## ̃
b(λ) =
μ
μ+λ
so that
p
jk
## =
μ
μ+λ
## (
λ
μ+λ
## )
k−j+1
,  j≥1,k≥j.(30)
As  expected  due  to  memoryless  property,  PASTA,  and  that  the  minimum  of  two  independent
exponential random variables is an exponential random variable, in theM/M/1 settingp
jk
has a
Geometric distribution with parameter
μ
μ+λ
## .
Using the transition probabilities in (29) (and these forp
## 0j
), the steady-state distribution of the
number of customers in the system observed by an arrival is as follows.
Theorem 4.Suppose that
## ∞
## ∑
i=1
i−1
## ∏
j=0
## 1−
## ̃
h
j
## (
λ
j+1
α
j+1
## )
## ̃
b
j+1
## (λ
j+1
## )
## <∞.(31)
Then, the steady-state distribution of the number of people in anM
n
## /G
n
/1queue observed by an
arrival is
## ̄
## P
a
## (i) =
## ̄
## P
a
## (0)
i−1
## ∏
j=0
## 1−
## ̃
h
j
## (
λ
j+1
α
j+1
## )
## ̃
b
j+1
## (λ
j+1
## )
## ,(32)

## 14
where from (32) and
## ∑
## ∞
i=0
## ̄
## P
a
(i) = 1, we have
## ̄
## P
a
## (0) =
## 1
## 1 +
## ∑
## ∞
i=1
i−1
## ∏
j=0
## 1−
## ̃
h
j
## (
λ
j+1
α
j+1
## )
## ̃
b
j+1
## (λ
j+1
## )
## .(33)
Comparing (15) and (32), we next relate the steady-state probability of havingicustomers in
the system at an arrival epoch to the steady-state probability of havingicustomers in the system
at an arbitrary time.
Observation 5.In  anM
n
## /G
n
/1  system,  the  relation  between  the  steady-state  probability  of
havingicustomers in the system at arrival (or departure) epochs and at arbitrary times is given
by:
## ̄
## P
a
## (i) =
λ
i
## P(i)
## ∑
## ∞
k=0
λ
k
## P(k)
## .(34)
Note that when arrival rates are identical,λ
i
=λfori= 0,1,..., the PASTA property holds and
therefore
## ̄
## P
a
(i) =P(i).
Observation 5 indicates that
## ̄
## P
a
(i) can be obtained usingP(i) given in Theorem 2. More inter-
estingly, Observation 5 together with Theorem 4 provide an alternative proof for Theorem 2 using
that:
Lemma 1.In  anM
n
## /G
n
/1system,  the  relation  between  the  steady-state  probability  of  havingi
customers in the system at arbitrary times and at arrival (or departure) times is given by:
P(i) =P(0)
λ
## 0
## ̄
## P
a
## (i)
λ
i
## ̄
## P
a
## (0)
i≥0.(35)
Similar to the analysis in Section 4.1.2, we next obtain the steady-state service rate of a customer
observed at arrival epochs when there areicustomers in the system, ˆμ
a
i
## .
Observation 6.The  equilibrium  service  rate  of  a  customer  in  theM
n
## /G
n
/1  system  at  arrival
epochs when there areicustomers in the system is
## ˆμ
a
i
## =
λ
i−1
λ
i
## ˆμ
i
## =
λ
i−1
## ̃
b
i
## (
λ
i
## )
## 1−
## ̃
h
i−1
## (
λ
i
α
i
## )
## .(36)
Observation 6 indicates that the steady-state utilization of the system observed by arrivals who
findicustomers in the system,
λ
i−1
## ˆμ
a
i
, is identical to the steady-state utilization of the system when
there areicustomers in the system,
λ
i
## ˆμ
i
## .

## 15
## 4.3.M
n
## /G
n
/1System when State-Dependence is for a Finite Number of States
In this section we obtain a closed form expression for the steady-state probability that there are no
customers in the system,P(0), when state-dependence is for a finite number of states. We assume
that there exists ak <∞such that for anyi≥k,λ
i
andb
i
are independent of the number of people
in the system, i.e.,k= min
i
## {λ
i
## ,b
i
## (·),α
i
## :λ
i
## =λ
i+1
## =...,b
i
## (·) =b
i+1
## (·) =...,α
i
## =α
i+1
## =...= 1}. This
queue is state-dependent fori < kand has the same arrival rate and service time distribution for
i≥k. We assume thatλ
k
## /μ
k
<1 to ensure that the system is stable.
To obtainP(0), we use QD. Consider the auxiliary queue defined in Section 4.1.3 forκ=k. Let
ρ
b
andμ
b
denote the server utilization and the rate of the first exceptional service times in this
auxiliary queue, respectively. Note that the service time densities,b
i
(·), in this system are identical
fori > k. Therefore, the rate of the service time in the auxiliary queue isμ
k
with probabilityρ
b
andμ
b
with probability (1−ρ
b
), so that
ρ
b
## =ρ
b
λ
k
μ
k
## +
## (
## 1−ρ
b
## )
λ
k
μ
b
leading to
ρ
b
## =
λ
k
μ
k
μ
b
μ
k
## +λ
k
## (μ
k
## −μ
b
## )
## .(37)
To obtain the utilization of the auxiliary queue,ρ
b
, we derive the average rate of the exceptional
first service times,μ
b
## .
Lemma 2.The average exceptional first service time in the busy period of the auxiliary queue is,
## 1
μ
b
## =
## 1
μ
k
## −
## 1
λ
k
## +
k−1
## ∑
j=1
k−1
## ∏
i=j
## 1
α
i+1
## (
## 1
μ
j
## −
## 1
λ
j
## )
## ̃
b
i+1
## (λ
i+1
## )
## 1−
## ̃
h
i
## (
λ
i+1
α
i+1
## )
## +
## 1
μ
## 1
## ̃
b
## 1
## (λ
## 1
## )
## 1−
## ̃
h
## 0
## (
λ
## 1
α
## 1
## )
k−1
## ∏
i=1
## 1
α
i
## ̃
b
i+1
## (λ
i+1
## )
## 1−
## ̃
h
i
## (
λ
i+1
α
i+1
## )
## .(38)
Note that Sigman and Yechiali (2007) provide the expected conditional stationary remaining service
time in anM/G/1 queue. Lemma 2 extends their result to theM
n
## /G
n
/1 queue.
Using (15), (22), and (23) the probability of having no customers in this system can be obtained
as follows.
Theorem 5.The steady-state probability of having no customers in theM
n
## /G
n
/1system in which
the arrival rates and service times are state-dependent for a finite number of states is
## P(0) =
## 1−ρ
b
λ
## 0
λ
k
k−1
## ∏
i=0
## 1−
## ̃
h
i
## (
λ
i+1
α
i+1
## )
## ̃
b
i+1
## (λ
i+1
## )
## + (1−ρ
b
## )
## (
## 1 +
## ∑
k−1
j=1
λ
## 0
λ
j
j−1
## ∏
i=0
## 1−
## ̃
h
i
## (
λ
i+1
α
i+1
## )
## ̃
b
i+1
## (λ
i+1
## )
## )
## .(39)
Substituting (39) into Theorems 2 provides a closed form expression for all steady-state proba-
bilities for systems where the arrival rates and service times are state-dependent for a finite number
of states.

## 16
-  Analysis ofM
n
## /G
n
## /1/K
In  this  section,  we  consider  a  state-dependent  queue  with  a  finite  bufferK,M
n
## /G
n
/1/K.  This
queue is identical to anM
n
## /G
n
/1 queueing system withλ
i
= 0 fori≥K(and, of course, it has no
issue of stability).
## 5.1.  Time Average Analysis
LetP
## F
(i) denote the steady-state probability of havingi
## (
0≤i≤K
## )
customers in this system with
Finite buffer. If the buffer size of the system is 1,K= 1, there is no state dependency andα
## 1
= 1 by
definition, thus the steady-state distribution of the number of people in the system can be obtained
fromP
## F
## (0) +P
## F
(1) = 1 andλ
## 0
## P
## F
## (0) =μ
## 1
## P
## F
(1) as (see e.g., Gross and Harris, 2011)
## P
## F
## (0) =
μ
## 1
λ
## 0
## +μ
## 1
## ,(40)
## P
## F
## (1) =
λ
## 0
λ
## 0
## +μ
## 1
## .(41)
Now consider a system with a buffer size larger than 1,K >1. We make the following important
observation.
Observation 7.Comparing the transitions in theM
n
## /G
n
/1/Kwith the ones in theM
n
## /G
n
## /1,
we observe that the transitions up to statesi= 0,···,K−1 in both systems are identical. The
difference  between  these  two  systems  is  that  all  transitions  that  take  theM
n
## /G
n
/1  to  a  state
greater  thanKare  lost  in  theM
n
## /G
n
/1/K.  This  means  that  the  transition  rates  in  the  states
i= 0,···,K−1 are identical in both systems.
Observation 7 emphasizes the equivalency between the transition rates in theM
n
## /G
n
/1/Kand
the ones in the B&D process, discussed in Observation 3, for statesi= 0,...,K−1. This observation
enables  us  to  solve  theM
n
## /G
n
/1/Kqueue  using  the  derivations  for  theM
n
## /G
n
/1  system  in  a
similar fashion that theM
n
## /M
n
/1/Kqueue is solved using theM
n
## /M
n
/1 ( similar to Gross and
Harris, 2011, page 76):
## P
## F
## (i) =
λ
## 0
## P
## F
## (0)
λ
i
i−1
## ∏
j=0
λ
j+1
μ
j+1
,  i= 1,...,K.(42)
Observation 7 allows us to easily obtain the steady-state probability of havingi < Kpeople in
theM
n
## /G
n
/1/K. We note that Gupta and Rao (1998) derive a direct solution of a special case of
our finite buffer queue using the supplementary variable method that we used to solve the infinite
buffer  case.  This  method  of  course  leads  to  the  same  solution  for  their  special  case,  but  is  less
elegant given the analysis in Section 4 and Observation 7.

## 17
Corollary 2.The  steady-state  distribution  of  the  number  of  people  in  anM
n
## /G
n
/1/Kqueue,
## P
## F
(i), is
## P
## F
## (i) =
λ
## 0
## P
## F
## (0)
λ
i
i−1
## ∏
j=0
## 1−
## ̃
h
j
## (
λ
j+1
α
j+1
## )
## ̃
b
j+1
## (λ
j+1
## )
,  i= 1,...,K−1(43)
whereμ
## 0
## =μ
## 1
and
## ̃
h
i
## (
## ·
## )
is given in (17).
We next obtain the steady-state probability of having exactly 0 andKcustomers in the system
using an auxiliaryM/G/1/1 queue with the following (a) arrival and (b) service processes:
Step (a):jobs arrive to the auxiliary queue according to a Poisson process with a rate ofλ
## K−1
## .
Step (b):the distribution of the first service time in the busy period of the auxiliary queue is
the distribution of the conditional residual service time in the originalM
n
## /G
n
/1/Kqueue given
that there areK−1 customers in the system, i.e., the equilibrium remaining service times given
that there areK−1 customers in the system.
## Let 1/μ
## F
b
andP
## A
## F
## (i)
## (
i= 0,1
## )
denote the mean service times and distribution of number of people
in this auxiliary queue, respectively. Then, using (40) and (41) we have,
## P
## A
## F
## (0) =
μ
## F
b
λ
## K−1
## +μ
## F
b
## ,(44)
## P
## A
## F
## (1) =
λ
## K−1
λ
## K−1
## +μ
## F
b
## .(45)
Therefore,  to  obtainP
## A
## F
(i),  we  need  to  derive  the  mean  of  the  service  times,  1/μ
## F
b
## .  Noting
that  Observation  7  demonstrates  that  theM
n
## /G
n
/1  andM
n
## /G
n
/1/Kare  equivalent  for  states
i= 0,...,K−1, 1/μ
## F
b
can be obtained by substitutingk=K−2 in (38) as:
Corollary 3.The average of the exceptional first service time in the auxiliary queue is,
## 1
μ
## F
b
## =
## 1
μ
## K−1
## −
## 1
λ
## K−1
## +
## K−2
## ∑
j=1
## K−2
## ∏
i=j
## 1
α
i+1
## (
## 1
μ
j
## −
## 1
λ
j
## )
## ̃
b
i+1
## (λ
i+1
## )
## 1−
## ̃
h
i
## (
λ
i+1
α
i+1
## )
## −
## 1
μ
## 1
## ̃
b
## 1
## (λ
## 1
## )
## 1−
## ̃
h
## 0
## (
λ
## 1
α
## 1
## )
## K−2
## ∏
i=1
## 1
α
i
## ̃
b
i+1
## (λ
i+1
## )
## 1−
## ̃
h
i
## (
λ
i+1
α
i+1
## )
## .(46)
LetF
## F
## (i)  :=
## ∑
i
j=0
## P
## F
(j).  Using  Observation  4  and  considering  that  theM
n
## /G
n
/1  and
## M
n
## /G
n
/1/Kare equivalent, the probability of havingi= 0,1 jobs in the auxiliary queue,P
## A
## F
## (i),
is identical to the probability of havingK+i−1 customers in the original queue,P
## F
(K+i−1),
given that there are more thanK−2 customers in the system.
Corollary 4.The steady-state probability of havingi=K−1, Kcustomers in anM
n
## /G
n
## /1/K
is
## P
## F
## (K−1) =
## (
## 1−F
## F
## (K−2)
## )
## P
## A
## F
## (0),(47)
## P
## F
## (K) =
## (
## 1−F
## F
## (K−2)
## )
## P
## A
## F
## (1).(48)

## 18
Considering (43), (44) and (47), the probability that the system is empty,P
## F
(0), is
## P
## F
## (0) =
## P
## A
## F
## (0)
λ
## 0
λ
## K−1
## K−2
## ∏
j=0
## 1−
## ̃
h
j
## (
λ
j+1
α
j+1
## )
## ̃
b
j+1
## (λ
j+1
## )
## +P
## A
## F
## (0)
## (
## 1 +
## ∑
## K−2
i=1
λ
## 0
λ
i
i−1
## ∏
j=0
## 1−
## ̃
h
j
## (
λ
j+1
α
j+1
## )
## ̃
b
j+1
## (λ
j+1
## )
## )
## .(49)
Substituting  (49)  in  (43),  we  can  obtainP
## F
(i)  fori= 1,...,K−1.  Therefore,P
## F
(K)  can  be
obtained using (48).
5.2.  Analysis at Arrival Epochs
## Let
## ̄
## P
a
## F
(n) denote the steady-state probability that anArrival observesncustomers in the system.
Unlike theM
n
## /G
n
/1 system, in theM
n
## /G
n
/1/Ksystem the distribution of the number of cus-
tomers seen by an arrival is not identical to the steady-state distribution of the number of customers
seen by a departure. The reason is that not all arriving customers are accepted to the system. Let
## ̄
## P
d
## F
(n) denote the steady-state probability that adeparture observesncustomers behind. We first
determine the relation between
## ̄
## P
a
## F
(n) and
## ̄
## P
d
## F
## (n).
Lemma 3.The relation between the distribution of the number of customers in the system observed
by an arrival and the one seen behind a departure is
## ̄
## P
a
## F
## (i) =
## ̄
## P
d
## F
## (i)(1−
## ̄
## P
a
## F
(K))i= 0,1,...,K−1.(50)
Note that if the arrival rate to the system when there areKpeople in the system is zero,λ
## K
## = 0,
the probability that an arrival observesKcustomers in the system is also zero,
## ̄
## P
a
## F
(K) = 0; then,
## ̄
## P
a
## F
## (i) =
## ̄
## P
d
## F
(i) fori= 0,...,K−1.
Corollary 5.The  steady-state  distribution  of  the  number  of  people  in  anM
n
## /G
n
/1/Kqueue
observed by an arrival is
## ̄
## P
d
## F
## (i) =
## ̄
## P
d
## F
## (0)
i−1
## ∏
j=0
## 1−
## ̃
h
j
## (
λ
j+1
α
j+1
## )
## ̃
b
j+1
## (λ
j+1
## )
i= 0,1,...,K−1(51)
where from (51) and
## ∑
## K−1
i=0
## P
d
## F
(i) = 1, we have
## ̄
## P
d
## F
## (0) =
## 1
## 1 +
## ∑
## K−1
i=1
i−1
## ∏
j=0
## 1−
## ̃
h
j
## (
λ
j+1
α
j+1
## )
## ̃
b
j+1
## (λ
j+1
## )
## .(52)
Considering Lemma 3 and Corollary 5, we can obtain the steady-state probability that an arrival
observesn(n < K) customers in the system,
## ̄
## P
a
## F
(n). To obtain
## ̄
## P
a
## F
(K), we can use the auxiliary
queue defined in Section 5.1. Then, considering (48), we get
## ̄
## P
a
## F
## (K) =
## (
## 1−
## ̄
## F
## F
## (K−2)
## )
## P
## A
## F
## (1),(53)
where
## ̄
## F
## F
## (i) :=
## ∑
i
j=0
## ̄
## P
a
## F
## (j).

## 19
## 6.  Summary
In this paper we considered state-dependent queueing systems where the arrival rates and service
times depend on the number of customers in the system. We allowed the service rate to change
at  arrivals  and  the  distribution  of  the  service  times  to  change  when  a  new  service  starts.  We
analyzed such systems at both arbitrary times and arrival epochs and obtained the steady-state
distribution of the number of customers in the system. We showed that theM
n
## /G
n
/1 systems can
be decomposed as in the standard B&D process. We also demonstrated that the state-dependent
queueing system with general service time distribution can be decomposed to new queues at any
given state. We note that obtaining the distribution of the sojourn time in theM
n
## /G
n
/1 model
is not straightforward. This follows because Littles law (and Littles distributional law) cannot be
applied since the future arrivals affect both the arrival and service rates (see e.g., Bertsimas and
## Nakazato, 1995).
## References
Abouee-Mehrizi,  H.,  B.  Balcioglu,  O.  Baron  2012.  “Strategies  for  a  Single  Product  Multi-Class
M/G/1 Queueing System”,Operations Research,Vol. 60, 803–812.
Altman, E., K. Avrachenkov, C. Barakat, R. Nunez-Queija 2002. “State-Dependent M/G/1 Type
Queueing Analysis for Congestion Control in Data Networks”,Computer NetworkVol. 39, 789–808.
Asmussen, S. 1991. “Ladder Heights and the Markov-ModulatedM/G/1 Queue”,Stochastic Pro-
cesses and their ApplicationsVol. 37, 313–326.
Baron, O. 2008. “Regulated random walks and the LCFS backlog probability: Analysis and appli-
cations”,Operations Research, Vol. 56, 471-486.
Bekker, R., S. C. Borst, O. J. Boxma, O. Kella 2004. “Queues with Workload-Dependent Arrival
and Service Rates”,Queueing SystemsVol. 46, 537–556.
Bekker, R., O. J. Boxma 2007. “An M/G/1 queue with adaptable service speed”,Stochastic Models
## Vol. 23, 373–396.
Bekker, R., G. M. Koole, B. F. Nielsen, T. B. Nielsen 2011. “Queues with waiting time dependent
service”,Queueing SystemsVol. 68, 61–78.
Bertsimas, D., D. Nakazato, 1995. “The Distributional Little?s Law and its Applications”,Opera-
tions ResearchVol. 43, 298–310.
Buzacott, J. A., J. G. Shanthikumar 1993.Stochastic Models of Manufacturing Systems, Prentice
## Hall.
Cohen, J. W. 1982. The Single Server Queue, North-Holland, Publishing Company.

## 20
Conway, R. W., W. L. Maxwell, L. W. Miller 1967.Theory of Scheduling, Dover Publications.
Cox, D. R., 1955. “A Use of Complex Probabilities in the Theory of Stochastic Processes”,Pro-
ceedings of the Cambridge Philosophical Society, Vol. 51, 313–319.
Vb Doorn, E. A., G. J. K. Regterschot. 1988. “Conditional PASTA”,OR Letters, Vol. 7, 229–232.
Gaver, D.P., and R.G. Miller. 1962. “Limiting distributions for some storage problems”,In: Studies
in Applied Probability and Management Science, 110–126.
Gross, D., C. M.,Harris. 2011. Fundamentals of Queueing Theory, John Wiley & Sons, New York.
Gupta,  U.  C.,  T.S.S.  Srinivasa  Rao  1998.  “On  the  Analysis  of  Single  Server  Finite  Queue  with
State Dependent Arrival and Service Processes:M
n
## /G
n
/1/K”,OR SpektrumVol. 20, 83–89.
Harris, C.M. 1967. “Queues with State-Dependent Stochastic Service Rates,”Operations Research,
## Vol. 15, 117–130.
Hokstad, P. 1975a. “THE G/M/m QUEUE WITH FINITE WAITING ROOM,”Scand J Statist,
## Vol. 12, 779–792.
Hokstad, P. 1975b. “A Supplementary Variable Technique Applied to theM/G/1 Queue,”Scand
## J Statist, Vol. 2, 95–98.
Kerner,   Y.  2008.  “The  Conditional  Distribution  of  the  Residual  Service  Time  in  theM
n
## /G/1
Queue,”Stochastic Models, Vol. 24, 364–375.
## Kleinrock, L. 1975. Queueing Systems, John Wiley & Sons, New York.
Medhi, J. 2002. Stochastic Models in Queueing Theory, Academic Press.
Perry, D., M. J. M. Posner 1990. “Control of Input and Demand Rates in Inventory Systems of
Perishable Commodities”,Operations ResearchVol. 37, 85–97.
Sigman, K., U. Yechiali. 2007. “Stationary remaining service time conditional on queue length”,
OR Letters, Vol. 35, 581–583.
Shanthikumar,  J. G. 1979. “On a single-server queue with state-dependent service,”Naval Research
## Logistics, Vol. 26, 305–309.
Regterschot,  G. J. K., J. H. A. de Smit 1986. “The QueueM/G/1 with Markov Modulated Arrivals
and Services,”Mathematics of Operations Research, Vol. 11, 465–483.
Takagi, H. 1993.Queueing Analysis, Volume 2, Elsevier: North Holland, The Netherlands.
Tijms, H.C. 2003. A First Course in Stochastic Models, John Wiley & Sons, Chichester.
Tijms, H.C., Van Hoorn, M.H., Federgruen, A. 1981. “Approximations for the steady-state prob-
abilities in the M/G/c queue,”Advanced Applied Probability, Vol. 13, 186–206.
Wang,  P.  P.  1996.  “Queueing  Models  with  Delayed  State-Dependent  Service  Times”,European
Journal of Operational ResearchVol. 88, 614–621.

## 21
Zhao, X., He, Q., Zhang, H. 2012. “On a Queueing System with State-dependent Service Rate,”
working paper.

## 22
## 7.  Proofs
Proof of Observation 2.Note that the Auxiliary queue is defined as anM
n
## /M
n
/1 queue
with arrival rateλ
κ+i
and service rateμ
κ+i
when there areicustomers in this queue. Therefore,
the steady-state distribution of the number of people in this queue can be obtained using (5) and
(6). Using (5), the probability of havingκ+ipeople in the original queue,P(κ+i), is
## P(κ+i) =
λ
## 0
## P(0)
λ
κ+i
κ+i−1
## ∏
j=0
λ
j+1
μ
j+1
## =
λ
## 0
## P(0)
λ
κ+i
## (
κ−1
## ∏
j=0
λ
j+1
μ
j+1
## )(
κ+i−1
## ∏
j=k
λ
j+1
μ
j+1
## )
## =
## (
λ
## 0
## P(0)
λ
κ
## P
## A
## (0)
κ−1
## ∏
j=0
λ
j+1
μ
j+1
## )(
λ
κ
## P
## A
## (0)
λ
κ+i
i−1
## ∏
j=0
λ
κ+j+1
μ
κ+j+1
## )
## ,(54)
whereP
## A
(0) denotes the probability of having no customers in the auxiliary queue.
We next prove that the first term in (54) is equal to
## (
1−F(κ−1)
## )
. SubstitutingP
## A
(0) given in
(6) into the first term in (54), we get
## (
λ
## 0
## P(0)
λ
κ
## P
## A
## (0)
κ−1
## ∏
j=0
λ
j+1
μ
j+1
## )
## =
## (
λ
## 0
## P(0)
λ
κ
κ−1
## ∏
j=0
λ
j+1
μ
j+1
## )(
## 1 +
## ∞
## ∑
i=1
λ
κ
λ
κ+i
i−1
## ∏
j=0
λ
κ+j+1
μ
κ+j+1
## )
## =
## (
λ
## 0
## P(0)
λ
κ
κ−1
## ∏
j=0
λ
j+1
μ
j+1
## )(
## 1 +
## ∞
## ∑
i=κ+1
λ
κ
λ
i
i−1
## ∏
j=κ
λ
j+1
μ
j+1
## )
## =
## (
λ
## 0
## P(0)
λ
κ
κ−1
## ∏
j=0
λ
j+1
μ
j+1
## +
## ∞
## ∑
i=κ+1
λ
## 0
## P(0)
λ
i
i−1
## ∏
j=0
λ
j+1
μ
j+1
## )
## =
## ∞
## ∑
i=κ
λ
## 0
## P(0)
λ
i
i−1
## ∏
j=0
λ
j+1
μ
j+1
## =
## (
1−F(κ−1)
## )
## .
Comparing the second term in (54) with (5), we find that the former is the probability of having
ipeople in the Auxiliary queue,P
## A
(i). Therefore, (54) is equivalent to (8),
## P(κ+i) =
## (
1−F(κ−1)
## )
## P
## A
## (i).
Supplementary Result for Proof of Theorem 2
Before we prove Theorem 2, we prove the following lemma. Letp
j
(η) denote the steady-state
density of the residual service time of the customer in service when there arejcustomers in the
system, assuming that such steady-state density exists. Then,
## Lemma 4.
## ∫
## ∞
u=η
e
## −λ
## 1
u
p
## ′
## 1
## (u)du=
## ∫
## ∞
u=η
e
## −λ
## 1
u
## (
λ
## 1
p
## 1
## (u)−λ
## 0
## P(0)b
## 1
## (u)−p
## 2
## (0)b
## 1
## (u)
## )
du(55)
## ∫
## ∞
u=η
e
## −λ
j
u
p
## ′
j
## (u)du=
## ∫
## ∞
u=η
e
## −λ
j
u
## (
λ
j
p
j
## (u)−α
j
p
j−1
## (
α
j
u
## )
λ
j−1
## −p
j+1
## (0)b
j
## (u)
## )
du.(56)

## 23
Proof of Lemma 4.
As we assume thatb
j
(·) are all absolutely continuous, a sufficient condition forp
j
(η) to exist is
that theM
n
## /G
n
/1 system is stable. Dividing both sides of (12) and (13) bydtand rearranging
them we get,
p
## 1
## (η,t)−p
## 1
## (η−dt,t+dt)
dt
## =p
## 1
## (η,t)λ
## 1
## −p
## 2
## (0,t)b
## 1
## (η)−λ
## 0
p
## 0
## (t)b
## 1
## (η) +
o(dt)
dt
## ,
p
j
## (η,t)−p
j
## (η−dt,t+dt)
dt
## =p
j
## (η,t)λ
j
## −p
j+1
## (0,t)b
j
## (η)−α
j
p
j−1
## (
ηα
j
## ,t
## )
λ
j−1
## +
o(dt)
dt
## .
Taking the limit asdt→0, we get:
p
## ′
## 1
## (η,t) =λ
## 1
p
## 1
## (η,t)−λ
## 0
p
## 0
## (t)b
## 1
## (η)−p
## 2
## (0,t)b
## 1
## (η),
p
## ′
j
## (η,t) =λ
j
p
j
## (η,t)−α
j
p
j−1
## (
α
j
η,t
## )
λ
j−1
## −p
j+1
## (0,t)b
j
## (η).
Assuming that the steady-state exists and taking the limitt→∞, we get:
p
## ′
## 1
## (η) =λ
## 1
p
## 1
## (η)−λ
## 0
## P(0)b
## 1
## (η)−p
## 2
## (0)b
## 1
## (η),(57)
p
## ′
j
## (η) =λ
j
p
j
## (η)−α
j
p
j−1
## (
α
j
η
## )
λ
j−1
## −p
j+1
## (0)b
j
## (η).(58)
Multiplying both sides of (57) and (58) bye
## −λ
j
u
and taking integral, we get (55) and (56).
Proof of Theorem 2.
We note thatp
j
## (∞) = 0,p
j
(0)≥0 forj >0, andP(0)>0 because we assume that the system
is stable. Also,
## ∫
## ∞
η=0
p
j
(η)dη=P(j) and similarly from (1)
## ∫
## ∞
η=0
α
j
p
j−1
## (α
j
η)dη=P(j−1). Then, by
settingη=λ
j
= 0 in Lemma 4, from (55) and (56) we get
## −p
## 1
## (0) =λ
## 1
## P(1)−λ
## 0
## P(0)−p
## 2
## (0)
## −p
j
## (0) =λ
j
## P(j)−λ
j−1
## P(j−1)−p
j+1
## (0).
Therefore, forj≥1
λ
j−1
## P(j−1)−p
j
## (0) =λ
j
## P(j)−p
j+1
## (0).
Note thatλ
j−1
## P(j−1)−p
j
(0) is independent ofjand must go to zero in the limit whenj→∞if
the system is stable (see e.g., Kerner, 2008). Therefore,
p
j+1
## (0) =λ
j
P(j),  j≥0.(59)
Note that (59) can be explained using level crossing as well. Considering levelj(number of cus-
tomers  in  the  system),λ
j
P(j)  is  the  rate  of  up-crossing  this  level  andp(j+ 1,0)  is  the  rate  of
down-crossing (i.e., the rate at which a departure leavesjcustomers behind).

## 24
Recalling thath
j
(·) denotes the steady-state density of the residual service time observed by an
arrival that seesjcustomers in the system, we have
h
j
## (η) =
p
j
## (η)
## ∫
## ∞
r=0
p
j
## (r)dr
## =
p
j
## (η)
## P(j)
## .(60)
## Therefore,
## ̃
h
j
## (s) =
## ∫
## ∞
r=0
e
## −sr
p
j
## (r)dr
## P(j)
## .(61)
Substituting (59) in (57) and (58), and multiplying both sides bye
## −λ
j
η
, we get after some algebra,
e
## −λ
## 1
η
## (p
## ′
## 1
## (η)−λ
## 1
p
## 1
## (η)) =−b
## 1
## (η)e
## −λ
## 1
η
## (λ
## 0
## P(0) +λ
## 1
## P(1))(62)
e
## −λ
j
η
## (p
## ′
j
## (η)−λ
j
p
j
## (η)) =−e
## −λ
j
η
## (
α
j
p
j−1
## (
α
j
η
## )
λ
j−1
## +λ
j
## P(j)b
j
## (η)
## )
## .(63)
Considering (61), Lemma 4, and recallingb
j
(∞) = 0 forj≥1 we get,
p
## 1
## (η) =e
λ
## 1
η
## ∫
## ∞
u=η
## (
b
## 1
## (u)e
## −λ
## 1
u
## (λ
## 0
## P(0) +λ
## 1
## P(1))
## )
du
p
j
## (η) =e
λ
j
η
## ∫
## ∞
u=η
## (
e
## −λ
j
u
## (
α
j
p
j−1
## (
α
j
u
## )
λ
j−1
## +λ
j
## P(j)b
j
## (u)
## )
## )
du.
Substituting (59) in the above equations, we get forη= 0
λ
## 0
## P(0) = (λ
## 0
## P(0) +λ
## 1
## P(1))
## ∫
## ∞
u=0
## (
b
## 1
## (u)e
## −λ
## 1
u
## )
du
λ
j−1
## P(j−1) =
## ∫
## ∞
u=0
## (
e
## −λ
j
u
## (
α
j
p
j−1
## (
uα
j
## )
λ
j−1
## +λ
j
## P(j)b
j
## (u)
## )
## )
du.
Solving the integral from right hand side of the above equations we get,
λ
## 0
## P(0) = (λ
## 0
## P(0) +λ
## 1
## P(1))
## ̃
b
## 1
## (
λ
## 1
## )
λ
j−1
## P(j−1) =λ
j−1
## P(j−1)
## ̃
h
j−1
## (
λ
j
α
j
## )
## +λ
j
## P(j)
## ̃
b
j
## (
λ
j
## )
## ,
because from (61) we have
## ∫
## ∞
u=0
e
## −λ
j
u
## (
α
j
p
j−1
## (
uα
j
## ))
du=P(j−1)
## ̃
h
j−1
## (
λ
j
α
j
## ).(64)
Finally, with
## ̃
h
## 0
## (·) =
## ̃
b
## 1
(·) andα
## 1
= 1 after some algebra and using induction we get for eachj≥1
## P(i) =
λ
## 0
## P(0)
λ
i
i−1
## ∏
j=0
## 1−
## ̃
h
j
## (
λ
j+1
α
j+1
## )
## ̃
b
j+1
## (λ
j+1
## )
## .
Standard arguments establish the rest of the theorem.

## 25
Proof of Theorem 3.
Settingη= 0 in Lemma 4, from (55) and (56) we get (similar to (64))
## P(1)s
## ̃
h
## 1
## (s)−p
## 1
## (0) =λ
## 1
## P(1)
## ̃
h
## 1
## (s)−
## ̃
b
## 1
## (s)
## (
p
## 2
## (0) +λ
## 0
## P(0)
## )
## (65)
## P(j)s
## ̃
h
j
## (s)−p
j
## (0) =λ
j
## P(j)
## ̃
h
j
## (s)−λ
j−1
## P(j−1)
## ̃
h
j−1
## (
s
α
j
## )
## −
## ̃
b
j
## (s)p
j+1
## (0).(66)
Substituting (59) in (65) and (66), we get
## P(1)s
## ̃
h
## 1
## (s)−λ
## 0
## P(0) =λ
## 1
## P(1)
## ̃
h
## 1
## (s)−
## ̃
b
## 1
## (s)
## (
λ
## 1
## P(1) +λ
## 0
## P(0)
## )
## (67)
## P(j)s
## ̃
h
j
## (s)−λ
j−1
## P(j−1) =λ
j
## P(j)
## ̃
h
j
## (s)−λ
j−1
## P(j−1)
## ̃
h
j−1
## (
s
α
j
## )
## −
## ̃
b
j
## (s)λ
j
## P(j).(68)
Now considering (67) we get:
## ̃
h
## 1
## (s) =
## (
λ
## 0
## P(0)−
## ̃
b
## 1
## (s)
## (
λ
## 1
## P(1) +λ
## 0
## P(0)
## )
## )
## (
## P(1)s−λ
## 1
## P(1)
## )
## .
## Substitutingλ
## 1
P(1) from (15) and recalling that
## ̃
h
## 0
## (·) =
## ̃
b
## 1
(·), we get
## ̃
h
## 1
## (s) =
## (
λ
## 1
s−λ
## 1
## )
## 
## 
## ̃
b
## 1
## (
λ
## 1
## )
## 1−
## ̃
b
## 1
## (
λ
## 1
α
## 1
## )
## (
## 1−
## ̃
b
## 1
## (s)
## )
## −
## ̃
b
## 1
## (s)
## 
## 
## .
Considering that
## ̃
h
## 0
## (·) =
## ̃
b
## 1
(·) andα
## 1
= 1, we get
## ̃
h
## 1
## (s) =
λ
## 1
s−λ
## 1
## [
## ̃
b
## 1
## (λ
## 1
## )
## 1−
## ̃
h
## 0
## (
s
α
## 1
## )
## 1−
## ̃
h
## 0
## (
λ
## 1
α
## 1
## )
## −
## ̃
b
## 1
## (s)
## ]
## .
Similarly, we can obtain
## ̃
h
j
(s) forj >1 using (68) as,
## ̃
h
j
## (s) =
λ
j
s−λ
j
## 
## 
## ̃
b
j
## (λ
j
## )
## 1−
## ̃
h
j−1
## (
s
α
j
## )
## 1−
## ̃
h
j−1
## (
λ
j
α
j
## )
## −
## ̃
b
j
## (s)
## 
## 
,  j≥1.
Proof of Observation 3.From Theorem 2 we have
## P
## (
i
## )
## =
λ
## 0
## P
## (
## 0
## )
λ
i
## Π
i−1
j=0
## 1−
## ̃
h
j
## (
λ
j+1
α
j+1
## )
## ̃
b
j+1
## (
λ
j+1
## )
## =λ
i−1
## 1−
## ̃
h
i−1
## (
λ
i
α
i
## )
λ
i
## ̃
b
i
## (
λ
i
## )
## P
## (
i−1
## )
Multiplying both sides byλ
i−1
and comparing the result with (3), we get ˆμ
i
as in (18).
Proof of Observation 4.Consider  the  auxiliary  queue.  We  define  a  continuous  time  MC
for the auxiliary queue similar to the one expressed in (12) and (13) with states (j,η) wherejis
the number of jobs in the auxiliary queue, whileηdenotes the remaining service time. We define

## 26
g
j
(η,t) as the probability that there arejjobs in the auxiliary queue, and remaining service time
isηat timet. Therefore,
g
## 1
## (η−dt,t+dt) =g
## 1
## (η,t)(1−λ
κ+1
dt) +g
## 2
## (0,t)b
κ+1
## (η)dt+g
t
## (0,0)λ
κ
b
## A
## 0
(η)dt, j= 1,(69)
g
j
## (η−dt,t+dt) =g
j
## (η,t)(1−λ
κ+j
dt) +g
j−1
## (η,t)λ
κ+j−1
dt+g
j+1
## (0,t)b
κ+j
(η)dt, j≥2,(70)
whereb
## A
## 0
(·) is the steady-state service time density of a job that finds 0 jobs in this queue.
Now consider the original system defined in (12) and (13). Given that there are more thanκ−1
customers in the system, (12) and (13) reduced to the same equations as given in (69) and (70)
whereb
## A
## 0
(·)  is  the  equilibrium  service  time  densities  of  customers  that  findκcustomers  in  the
original system (Step 2 of the definition of the auxiliary queue). Thus, the steady-state distribution
of the number of jobs in the auxiliary queue,P
## A
(i), is identical to the steady-state state distribution
of the number of customers in the original queue given that there are more thanκcustomers in
the system,P(κ+i).
Proof of Corollary 1.The proof is similar to the proof of Theorem 2.2.2 in Kerner (2008).
Van Doorn and Regterschot (1988) define the adapted LAA as the LAA conditioning on the state
of the system, and show that under the adapted LAA PASTA holds. We next establish that the
adapted LAA holds in our settings. LetX(t) denote the state of the system, andN
s
be the Poisson
process  that  generates  the  future  arrivals  when  the  state  of  the  system  isX(t) =s.  Then,  for
everyswe have{N
s
(t+u)−N
s
(t),u≥0}andX(t) are independent and the adaptive LAA holds.
Therefore, Theorem 1 in Van Doorn and Regterschot (1988) holds.
Proof of Theorem 4.
We  first  obtain  the  transition  probabilitiesp
## 0k
## .  Considerp
## 00
,  the  probability  that  the  next
departing  customer  leaves  no  customer  behind  given  that  the  last  departing  customer  left  no
customer behind,P
## (
## M
n+1
## = 0|M
n
## = 0
## )
. This probability is equal to the probability of having no
arrivals during the next service time, i.e., it is
## ̃
b
## 1
## (λ
## 1
) (e.g., Conway 1967, page 171). Therefore,
p
## 00
## =
## ̃
b
## 1
## (λ
## 1
## ).(71)
Next considerP
## 01
. The probability that the next departing customer leaves one customer behind
given that the last departing customer left no customer behind,P
## (
## M
n+1
## = 1|M
n
## = 0
## )
. This proba-
bility is equal to the probability of one arrival during the next service time. The only sample path
that would lead to this event is that there is exactly one arrival during the sojourn time of the
departing customer.  Because this sojourn time is identical to the service time  of this customer,
the probabilityp
## 01
is equal to the probability that(i)a customer arrives after the service time

## 27
starts,
## (
## 1−
## ̃
b
## 1
## (λ
## 1
## )
## )
and(ii)no customers arrive during the remaining service time observed by
this arrival. Noting that this arrival sees one customer in the system upon the arrival, the equi-
librium remaining service time observed by this arrival ish
## 1
(·). Considering that the rate of the
residual service time is modified byα
## 2
after this customer joins the queue, the probability that no
customers arrive during the remaining service time observed by this arrival is
## ̃
h
## 1
## (
λ
## 2
α
## 2
## ). Therefore,
p
## 01
## =
## (
## 1−
## ̃
b
## 1
## (λ
## 1
## )
## )
## ̃
h
## 1
## (
λ
## 2
α
## 2
## )
## .(72)
With a similar logic, the probability that the next departing customer leaveskcustomers behind
given that the last departing customer left no customer behind,P
## (
## M
n+1
=k|M
n
## = 0
## )
, is equal to
the probability ofkarrivals during the next service time. This probability is equal to the probability
that  a  customer  arrives  after  the  first  service  time  starts,
## (
## 1−
## ̃
b
## 1
## (λ
## 1
## )
## )
,  followed  by  a  customer
arrival during the remaining service times of all arrivals that seei < kcustomers in the system,
each with probability
## (
## 1−
## ̃
h
i
## (
λ
i+1
α
i+1
## )
## )
, and no arrival during the remaining service time once there
arekcustomers in the system,
## ̃
h
k
## (
λ
k+1
α
k+1
). Recalling our definition
## ̃
h
## 0
## (·) =
## ̃
b
## 1
(·), we have,
p
## 0k
## =
## ̃
h
k
## (
λ
k+1
α
k+1
## )
k−1
## ∏
i=0
## (
## 1−
## ̃
h
i
## (
λ
i+1
α
i+1
## )
## )
## .(73)
Using the transition probabilities in (29) derived in the body of the paper and (73) we next derive
the steady-state probabilities of the embedded MC. Considering (24), we need to derive the steady-
state distribution of the number of customers in system using the embedded MC. Note that the
steady-state probability that a departure leaveskcustomers behind satisfiesP
d
## (k) =
## ∑
## ∞
j=0
## P
d
## (j)p
jk
## .
First considerP
d
## (0):
## P
d
## (0) =P
d
## (0)p
## 00
## +P
d
## (1)p
## 10
## =P
d
## (0)
## ̃
b
## 1
## (λ
## 1
## ) +P
d
## (1)
## ̃
b
## 1
## (λ
## 1
## )
## ⇒P
d
## (1) =P
d
## (0)
## 1−
## ̃
b
## 1
## (λ
## 1
## )
## ̃
b
## 1
## (λ
## 1
## )
## .(74)
Next considerP
d
## (1):
## P
d
## (1) =P
d
## (0)p
## 01
## +P
d
## (1)p
## 11
## +P
d
## (2)p
## 21
## =P
d
## (0)
## (
## 1−
## ̃
b
## 1
## (λ
## 1
## )
## )
## ̃
h
## 1
## (
λ
## 2
α
## 2
## )
## +P
d
## (1)
## (
## 1−
## ̃
b
## 1
## (λ
## 1
## )
## )
## ̃
h
## 1
## (
λ
## 2
α
## 2
## )
## +P
d
## (2)
## ̃
b
## 2
## (λ
## 2
## ).
## (75)
SubstitutingP
d
(1) from (74) to (75), we get
## P
d
## (2) =P
d
## (0)
## 1
## ∏
j=0
## 1−
## ̃
h
j
## (
λ
j+1
α
j+1
## )
## ̃
b
j+1
## (λ
j+1
## )
## .
The rest of the probabilities can be obtained similarly.

## 28
Proof of Corollary 2.
Substituting (18) in (3) we get
λ
i
## P
## F
## (
i
## )
## =
λ
i+1
## ̃
b
i+1
## (
λ
i+1
## )
## 1−
## ̃
h
i
## (
λ
i+1
α
i+1
## )
## P
## F
## (
i+ 1
## )
## .
## Therefore,
## P
## F
## (
i+ 1
## )
## =
λ
i
λ
i+1
## 1−
## ̃
h
i
## (
λ
i+1
α
i+1
## )
## ̃
b
i+1
## (
λ
i+1
## )
## P
## F
## (
i
## )
## ,
which after some algebra leads to (43).
Proof of Lemma 1.(34) is equivalent to
## P(i) =
## ̄
## P
a
## (i)
## ∑
## ∞
k=0
λ
k
## P(k)
λ
i
## .(76)
Using (76) we getP(0) as,
## P(0) =
## ̄
## P
a
## (0)
## ∑
## ∞
k=1
λ
k
λ
## 0
## P(k)
## 1−
## ̄
## P
a
## (0)
## .(77)
Using (76) and (77), we obtainP(i) as a function ofP(0) given in (35).
Proof of Observation 6.The  proof  is  based  on  Theorem  4  and  similar  to  the  proof  of
## Observation 3.
Proof of Lemma 2.
Noting that 1/μ
b
## =−
d
## ̃
h
κ
## (s)
ds
## |
s=0
, by taking the derivative of (17) with respect tosand setting
s= 0, we get:
## 1
μ
b
## =−
d
## ̃
h
k
## (s)
ds
## |
s=0
## =
λ
k
## (
s−λ
k
## )
## 2
## [
## ̃
b
k
## (λ
k
## )
## 1−
## ̃
h
k−1
## (
s
α
k
## )
## 1−
## ̃
h
k−1
## (
λ
k
α
k
## )
## −
## ̃
b
k
## (s)
## ]
## |
s=0
## −
λ
k
## (
s−λ
k
## )
## [
## −
## ̃
b
k
## (λ
k
## )
## 1−
## ̃
h
k−1
## (
λ
k
α
k
## )
d
## ̃
h
k−1
## (
s
α
k
## )
ds
## −
d
## ̃
b
k
## (s)
ds
## ]
## |
s=0
## =−
## 1
λ
k
## +
## 1
μ
k
## +
## [
## ̃
b
k
## (λ
k
## )
## 1−
## ̃
h
k−1
## (
λ
k
α
k
## )
d
## ̃
h
k−1
## (
s
α
k
## )
ds
## |
s=0
## ]
## .
We prove the result by induction. Fork= 1 we haveα
## 1
= 1 so that
## 1
μ
b
## =−
## 1
λ
## 1
## +
## 1
μ
## 1
## +
## [
## ̃
b
## 1
## (λ
## 1
## )
## 1−
## ̃
b
## 1
## (
λ
## 1
α
## 1
## )
d
## ̃
b
## 1
## (
s
α
## 1
## )
ds
## |
s=0
## ]
## =−
## 1
λ
## 1
## +
## 1
μ
## 1
## −
## [
## ̃
b
## 1
## (λ
## 1
## )
## 1−
## ̃
b
## 1
## (
λ
## 1
α
## 1
## )
## 1
μ
## 1
## ]
## ,
which with
## ̃
h
## 0
## (·) =
## ̃
b
## 1
(·) is equivalent to (38) fork= 1. Now suppose (38) holds forκ=m−1, i.e.,
## −
d
## ̃
h
m−1
## (s)
ds
## |
s=0
## =
## 1
μ
m−1
## −
## 1
λ
m−1
## +
m−2
## ∑
j=1
m−2
## ∏
i=j
## 1
α
i+1
## (
## 1
μ
j
## −
## 1
λ
j
## )
m−2
## ∏
i=j
## ̃
b
i+1
## (λ
i+1
## )
## 1−
## ̃
h
i
## (
λ
i+1
α
i+1
## )

## 29
## −
## 1
μ
## 1
m−2
## ∏
i=1
## 1
α
i
m−2
## ∏
i=0
## ̃
b
i+1
## (λ
i+1
## )
## 1−
## ̃
h
i
## (
λ
i+1
α
i+1
## )
## (78)
We next show that it holds fork=m.
## 1
μ
b
## =−
## 1
λ
m
## +
## 1
μ
m
## +
## [
## ̃
b
m
## (λ
m
## )
## 1−
## ̃
h
m−1
## (
λ
m
α
m
## )
d
## ̃
h
m−1
## (
s
α
m
## )
ds
## |
s=0
## ]
## =−
## 1
λ
m
## +
## 1
μ
m
## +
## [
## ̃
b
m
## (λ
m
## )
## 1−
## ̃
h
m−1
## (
λ
m
α
m
## )
## 1
α
m
d
## ̃
h
m−1
## (s)
ds
## |
s=0
## ]
## (79)
Substituting (78) in (79), we get (38) forκ=m, which completes the proof.
Proof of Theorem 5.Based on Observation 4, we have
## P(k) =
## (
1−F(k−1)
## )
## P
## A
## (0).
SubstitutingP(k) andF(k−1) from (15), we get
λ
## 0
## P(0)
λ
k
k−1
## ∏
i=0
## 1−
## ̃
h
i
## (
λ
i+1
α
i+1
## )
## ̃
b
i+1
## (λ
i+1
## )
## =
## 
## 
## 1−
k−1
## ∑
j=0
λ
## 0
## P(0)
λ
j
j−1
## ∏
i=0
## 1−
## ̃
h
i
## (
λ
i+1
α
i+1
## )
## ̃
b
i+1
## (λ
i+1
## )
## 
## 
## (1−ρ
b
## )
resulting in (39) after some algebra.
Proof of Lemma 3.LetN
a
denote the number of customers in the system seen by an arrival.
## Then,
## ̄
## P
a
## F
(i) =P
## (
## N
a
## =i|accepted
## )
## P
## (
accepted
## )
## +P
## (
## N
a
## =i|notaccepted
## )
## P
## (
notaccepted
## )
## .(80)
By level crossing argument for statesi < K, the frequency of transitions from stateito state
i+ 1 is equal to the frequency of transitions from statei+ 1 to statei. Therefore, the probability
that an arriving customer observesipeople in the system given that she is accepted to the queue,
## P
## (
## N
a
## =i|accepted
## )
, is identical to the probability that a departing customer leavesipeople behind,
## ̄
## P
d
## F
(i). Moreover, for statesi<K,P
## (
## N
a
## =i|notaccepted
## )
is zero. Therefore,
## ̄
## P
a
## F
## (i) =
## ̄
## P
d
## F
## (i)
## (
## 1−
## ̄
## P
a
## F
## (K)
## )
## +
## (
## 0
## )
## ̄
## P
a
## F
## (K)
## =
## ̄
## P
d
## F
## (i)
## (
## 1−
## ̄
## P
a
## F
## (K)
## )
,  i= 0,...,K−1.