

Finite-Buffer Queues with Workload-Dependent Service and
## Arrival Rates
## Ren ́e Bekker
## ∗
email: rbekker@win.tue.nl, phone: (0031) 71 2474332
Department of Mathematics & Computer Science
Eindhoven University of Technology
P.O. Box 513, 5600 MB Eindhoven, The Netherlands
## CWI
P.O. Box 94079, 1090 GB Amsterdam, The Netherlands
## Abstract
We consider M/G/1 queues with workload-dependentarrival rate,service speed,
andrestricted accessibility.  The admittance of customers typically depends on the
amount of work found upon arrival in addition to its own service requirement. Typical
examples are the finite dam, systems with customer impatience and queues regulated
by the complete rejection discipline. Our study is motivated by queueing scenarios
where the arrival rate and/or speed of the server depends on the amount of work
present, like production systems and the Internet.
First, we compare the steady-state distribution of the workload in two finite-buffer
models, in which the ratio of arrival and service speed is equal. Second, we find an ex-
plicit expression for the cycle maximum in an M/G/1 queue with workload-dependent
arrival and service rate. And third, we derive a formal solution for the steady-state
workload density in case of restricted accessibility. The proportionality relation be-
tween some finite and infinite-buffer queues is extended. Level crossings and Volterra
integral equations play a key role in our approach.
Keywords:restricted accessibility, finite buffer, impatience, state-dependent rates,
workload, cycle maximum, level crossings, Volterra integral equation.
## 1  Introduction
Queueing systems where the service speed is workload-dependent are well-known, specifi-
cally in the studies of dams and storage processes, see e.g. [3, 8, 12, 17, 19, 22]. Also, in
production systems the speed of the server often depends on the amount of work. This
is particularly true if the server is not being represented by a machine, but rather by a
human being; see [6, 27] for an example where the speed of the server is relatively low
when there is much work (stress) or when there is little work (laziness).
## ∗
Supported by a research grant from Philips Electronics
## 1

In addition to general service speeds, the rate at which jobs arrive at the system may also
depend on the amount of work present. In the human-server production system, we may
try to control the arrival rate of jobs to optimize server performance. In packet-switched
communication systems, the transmission rate of data connections may be dynamically
adapted based on the buffer content, see for instance [15, 16, 26, 29].  In particular,
feedback information on the buffer state provides the basis for the Transmission Control
Protocol (TCP) to carefully regulate the transmission rate of Internet flows.
These considerations led us to study single-server queues where the arrival rate and service
speed depend on the amount of work present (see also [4]).  Specifically, we consider
M/G/1-systems with restricted accessibility. In this paper, the admittance of customers
typically depends on the amount of work upon arrival in addition to its own service
requirement. In such systems, we may distinguish three main rejection disciplines: (i) the
finite dam, governed by the partial rejection rule (scenariof), (ii) systems with impatience
of customers depending on the amount of work found upon arrival (scenarioi), and (iii)
queues regulated by the complete rejection discipline (scenarioc).
The three main goals of our study are the following.  First, we establish relationships
between two queueing models with arrival ratesλ
i
(x) and service speedsr
i
(x), i= 1,2, for
which
λ
## 1
## (x)
r
## 1
## (x)
## =
λ
## 2
## (x)
r
## 2
## (x)
,∀x >0. Hereby, we extend results from [4] to queues with restricted
accessibility. These relationships between two queueing systems will allow us to obtain
results for a whole class of models from the analysis of one particular model.  This is
particularly useful in considering performance measures such as steady-state workload
densities and loss probabilities.
Turning to our second goal, we obtain an explicit (formal) expression for the cycle max-
imum in an M/G/1 queue with workload-dependent service and arrival rate. This may
be an important tool in determining the maximum buffer content. Exact results for such
systems are hardly known; we refer to Asmussen [2] for an overview on cycle maxima.
Third, we derive a formal solution for the steady-state workload density in finite-buffer
M/G/1 systems. Often, the density may be expressed as the solution of a Volterra integral
equation.  In some special cases, this reduces to an analytically tractable expression.
Otherwise, numerical methods are widely available, see e.g. [21, 24]. Another tool to solve
the workload density is the proportionality of the workload distribution between systems
with finite and infinite-buffer capacities. This relation is well-known for some traditional
queueing models (where work is depleted at unit rate), see [11, 12, 20]. Using a similar
sample path approach as in [20, 31], the proportionality relation is extended to similar
systems with workload-dependent arrival and service rate.
In classical queueing systems, the workload just before a customer arrival represents a
waiting time, and the workload right after an arrival instant may be identified with a
sojourn time. For such models, the rejection rules have a direct interpretation. Our first
discipline, the finite dam (scenariof), represents a system where every customer has a
bounded sojourn time; a rejected customer may enter the system but his sojourn time
is restricted. This model is also frequently used in the context of inventory and storage
processes. Due to the above mentioned proportionality, the finite dam is closely related
to the infinite-buffer version of the model [11, 12], and has thus been analyzed in detail,
see e.g. [12].
The second rejection discipline, scenarioi, reflects the fact that impatient customers are
only willing to wait a limited amount of time.  Results are also well-known for these
traditional queueing models, see e.g. [7, 10, 13, 23]. In queues with general service speeds,
## 2

the workload found upon arrival does in general not equal the waiting time. However,
these two quantities are closely related and the admittance may depend on the workload
upon arrival.
Finally, the third discipline, scenarioc, also exhibits the case in which customers have a
restricted sojourn time. In contrast with scenariof, rejected customers are completely
rejected and do not join the queue. This scenario is probably one of the more difficult to
analyze. Results are only known for the M/M/1 and M/D/1 case (see e.g. [10, 18]), and
the Ph/Ph/1 case [25]. Asymptotics for more general models are obtained in [32].
This paper is organized as follows. In Section 2 we introduce the general model. The
relations between two finite-buffer queues are given in Section 3. In Section 4, the finite
dam (scenariof) is studied and the proportionality relation between finite and infinite-
buffer systems is presented. First-exit probabilities and cycle maxima are considered in
Section 5. Section 6 examines scenariosiandc, and we conclude with some examples in
## Section 7.
2  Model description and preliminaries
In this section, we introduce the general model and obtain some preliminary results. Some
examples of typical finite-buffer models are given at the end of the section.
We first describe the general system. Customers arrive at a queueing system according
to a Poisson process with arrival rateλ(x) when the workload equalsx, x≥0; in other
words, the probability of an arrival in some interval (t, t+h) equalsλ(x)h+o(h) for
h↓0 when the work present at timetequalsx. We assume thatλ(·) is nonnegative,
left-continuous and has a right limit on [0,∞). The service requirement of customernis
denoted byB
n
, n= 1,2, . . ., whereasB
## 1
## , B
## 2
, . . .are assumed to be independent, identically
distributed with distributionB(·).
Depending on the service requirement and the amount of work found upon arrival, cus-
tomers may or may not be (fully) accepted.  In particular, if the workload just before
arrival equalsw, and the service requirement isb, then the amount of work right after the
arrival instant isg(w, b, K). We assume thatw≤g(w, b, K)≤w+b, whereKrepresents
a potential maximum buffer size (see the end of this section for some examples).
We allow the server to operate according to a general service rate (speed) function, a
function of the amount of work present.  We denote the service rate function byr:
[0,∞)→[0,∞), assume thatr(0) = 0 and thatr(·) is strictly positive, left-continuous,
and has a right limit on (0,∞).
In the general model, we defineV
g
(t) as the workload at timetand letW
g
n
be the workload
immediately before then-th arrival epoch. We denote the steady-state random variables
ofV
g
(t) andW
g
n
byV
g
andW
g
, and letV
g
(·) andW
g
(·) denote their distributions,
andv
g
(·) andw
g
(·) their densities. In the sequel, it is assumed thatλ(·), r(·), B(·) are
chosen such that the steady-state distribution of the infinite-buffer version, that is, for
g(w, b, K) =w+b, exists (and then for allg(·,·,·)). For details on stability and existence
of steady-state distributions, we refer to [8, 9].
## Define
## R(x) :=
## ∫
x
## 0
## 1
r(y)
dy,0< x <∞,
representing the time required for the system to become empty in the absence of any
arrivals, starting with workloadx. Note thatR(x)<∞, for allx >0, means that state
## 3

zero can be reached in a finite amount of time from any statex >0. A related quantity is
## Λ(x) :=
## ∫
x
## 0
λ(y)
r(y)
dy,0< x <∞,
which determines whether the workload process of the infinite buffer queue has an atom at
state zero. In case of finite buffers, some modification is required to regulate the workload
behavior for states that can not be attained.  Specifically, setr(x)≡1 andλ(x)≡λ
for allx >0 for whichP(g(y, B, K)> x) = 0), for all 0≤y < x. Then the workload
process has indeed an atom at state zero if and only if Λ(x)<∞for all 0< x <∞, as in
the infinite-buffer queue. In caseλ(·) is fixed (λ(x)≡λ), Λ(x) =λR(x) and we refer to
Asmussen [3, Ch. XIV] and Brockwellet al.[8] for more details.
Furthermore, consider the interarrival time and its corresponding workload decrement, i.e.,
the amount of work finished during the interarrival time. Denote byA
y
the conditional
workload decrement during the interarrival interval starting with workloady, i.e., the
event{A
y
> v}means that the workload is smaller thany−vupon the arrival of the next
customer. Note that the time required to move fromydown tovin the absence of any
arrivals equalsR(y)−R(v). Sincer(x)>0 for allx >0, it follows thatR(·) is strictly
increasing, which implies a one-to-one correspondence between the interarrival time and
its corresponding workload decrement.
The conditional distribution of the workload decrement during an interarrival interval was
already obtained in [4]:
Proposition 2.1.Let the workload just after an arrival bey(g(w, b, K) =y); then, for
y > v,
## P(A
y
> v) =e
## −
## ∫
y
u=y−v
λ(u)
r(u)
du
## .(1)
Turning back to the workload process{V
g
(t), t≥0}, we may define the process right
before jump epochs recursively, by
## W
g
n+1
= max(g(W
g
n
## , B
n
## , K)−A
n,g(W
g
n
## ,B
n
## ,K)
## ,0),(2)
whereA
n,g(·,·,·)
is the interarrival time between then-th and (n+1)-th customer, depending
on the workload right after then-th jump epoch. In between jumps, the workload process
is governed by the input rate function, and the process satisfies
dV
g
## (t)
dt
=r(V
g
## (t)).
This concludes the description of the dynamics of the system. We refer to Harrison and
Resnick [19] for a further discussion.
Special cases
As mentioned in Section 1, four important special cases of the general setting are queues
with infinite buffers, finite-buffer dams (scenariof), systems with customer impatience
(scenarioi), and queues regulated by the complete rejection discipline (scenarioc).
The model with infinite buffer size is discussed in [4] and is simply the model where every
customer is completely accepted. The finite-buffer dam - regulated by the partial rejection
discipline - originates from the study of water dams. The content of a dam is finite and
additional water just overflows.  In the context of queueing, this implies that then-th
## 4

arriving customer is admitted to the system if and only ifW
n
## +B
n
≤K. However, a
partially rejected (not fully accepted) customer may enter the system, but with restricted
service requirementK−W
n
## .
Models with customer impatience stem from classical queueing systems, with a server
working at unit speed. In that case, the workload upon arrival identifies a waiting time
and the impatience is represented by the fact that customers are willing to wait a limited
amount of timeK. In case of general service speeds, then-th arriving customer is accepted
ifW
n
≤Kand fully rejected otherwise (see [7] for some potential applications). Finally,
the system with complete rejections is probably one of the more difficult to analyze,
although the rejection rule is simple: then-th customer is admitted ifW
n
## +B
n
≤K, and
totally rejected otherwise.
Summarizing, these four scenarios may be represented as follows:
g(w, b, K) =
## 
## 
## 
## 
## 
## 
## 
w+b,infinite-buffer queue,
min(w+b, K),scenariof; finite dam,
w+bI(w≤K),scenarioi; customer impatience,
w+bI(w+b≤K),scenarioc; complete rejection discipline.
HereI(·) denotes the indicator function. Finally, we indicate the notational conventions
arising from the models. If we consider an arbitraryg(·,·,·), we add an indexg. The
infinite-buffer system is denoted by just omitting thegfrom the definitions of the general
model. The finite-buffer dam may be obtained by substitutingKforg. The models with
customer impatience and complete rejections are given by writingK, iandK, cforg,
respectively.
3  Relations between two finite-buffer queues
In this section, we analyze the workload relations between two (general) finite-buffer queues
that have the same ratio between arrival and service rate.  It turns out that a similar
relation as for infinite-buffer queues [4, Theorem 3.1] still holds (in fact, the infinite-buffer
queue is just a special case of the general setting studied here: Chooseg(w, b, K) =w+b,
for allw, b≥0). In addition, the formal solution of the steady-state workload density
is considered. However, we start with studying the relation between workloads at arrival
instants and arbitrary epochs.
In view of loss probabilities, the relation between the workload at jump epochs and arbi-
trary epochs is an important one. The following theorem extends results for infinite-buffer
queues [4, Theorem 3.2] to our setting.
Theorem 3.1.W
g
(0) =λ(0)V
g
## (0)/
## ̄
λ
g
, with
## ̄
λ
g
## :=
## ∫
## ∞
## 0
## +
λ(x)v
g
(x)dx+λ(0)V
g
(0), and for
allx >0,
w
g
## (x) =
## 1
## ̄
λ
g
λ(x)v
g
## (x).
Proof.Observe thatg(w, b, K)≤w+bensures that the expected cycle length is finite
and the workload process is thus ergodic. By level crossing theory, it then follows that
the workload density is well-defined. Moreover,g(w, b, K)≥wrules out scenarios of work
removal. Now, substituteg(W
g
, B, K) for everyW+Bin [4, Theorem 5.1] and the results
follow easily.
## 5

Note thatλ(x)≡λwould yield the PASTA property, which states that the workload at
an arbitrary time and the workload at an arrival epoch have the same distribution. With
respect to workload as the key performance measure, Thereom 3.1 may be viewed as a
generalization of the PASTA result.
In the infinite-buffer system, two models, with identical ratio between arrival and release
rate, can be related (see [4, Theorem 3.1 and 3.3]). This relation between two different
M/G/1 queues can be extended to the general model, as presented in the next theorem.
Theorem 3.2.Consider two queues of the model of Section 2, to be denoted as Models1
and2, such thatλ
## 1
## (x)/r
## 1
## (x) =λ
## 2
## (x)/r
## 2
(x), for allx >0. Then,W
g
## 1
## (0) =W
g
## 2
(0), and
for allx >0,
w
g
## 1
## (x) =w
g
## 2
## (x).(3)
## Also,
v
g
## 1
## (x)
v
g
## 2
## (x)
## =C
r
## 2
## (x)
r
## 1
## (x)
## ,(4)
withC=
λ
## 1
## (0)V
g
## 1
## (0)
λ
## 2
## (0)V
g
## 2
## (0)
ifΛ
i
(x)<∞for all0< x <∞, andC= 1ifΛ
i
(x) =∞for some
0< x <∞.
Before we prove the above theorem, we first derive the steady-state workload density.
Besides that the formal solution of this density is a slight extension of infinite-buffer
results, it turns out to be a useful tool to express the workload density in a more elegant
form in some special cases. Moreover, Equation (4) follows then directly by division.
Now, consider either of the two models and assume for the moment that the workload
process has an atom at state zero. We start by considering the level crossing equations
(see [14] for a survey on level crossings),
r(x)v
g
(x) =λ(0)V
g
(0)P(g(0, B, K)> x) +
## ∫
x
## 0
## +
λ(y)v
g
(y)P(g(y, B, K)> x)dy.(5)
This equation reflects the fact that the rate of crossing levelxfrom above should equal,
in steady-state, the rate of crossing levelxfrom below.
Note that in many finite-buffer systems, the workload is bounded by the capacityK,
as in scenariosfandc.  In that case,P(g(y, B, K)> K) = 0, and we only have to
consider 0< x≤K. In, for example, scenarioi, cases with workloads aboveKmay exist.
However, jumps occur only from workloads smaller thanK, and the range of integration
can be modified by (0,min(x, K)].
## Definez(y) :=λ(y)v
g
(y) and multiply both sides of (5) byλ(x)/r(x). We then obtain
z(x) =
λ(x)
r(x)
λ(0)V
g
(0)P(g(0, B, K)> x) +
## ∫
x
## 0
## +
λ(x)
r(x)
z(y)P(g(y, B, K)> x)dy.(6)
We now proceed as in Harrison & Resnick [19]: define the kernelK
g
(x, y) :=K
g
## 1
(x, y) :=
P(g(y, B, K)> x)λ(x)/r(x),0≤y < x <∞, and let its iterates be recursively defined by
## K
g
n+1
(x, y) :=
## ∫
x
y
## K
g
(x, z)K
g
n
(z, y)dz.(7)
## 6

Note that in, for instance, the infinite-buffer system,P(g(y, B, K)> x) = 1−B(x−y).
Moreover, observe that (6) is a Volterra integral equation of the second kind, and rewrite
it as
z(x) =λ(0)V
g
## (0)K
g
## (x,0) +
## ∫
x
## 0
## +
z(y)K
g
(x, y)dy.(8)
Iterate this relationN−1 times (see [19]):
z(x) =λ(0)V
g
## (0)
## N
## ∑
n=1
## K
g
n
## (x,0) +
## ∫
x
## 0
## +
z(y)K
g
## N
(x, y)dy.
Finally, define
## K
g,∗
(x, y) :=
## ∞
## ∑
n=1
## K
g
n
(x, y).(9)
If this sum is well defined, we havez(x) =λ(0)V
g
## (0)K
g,∗
(x,0).  However, we may
use the obvious boundK
g
(x, y)≤λ(x)/r(x) to show inductively thatK
n+1
(x, y)≤
(Λ(x, y))
n
λ(x)/(r(x)n!).  Hence, sinceK
n+1
(x, y)→0, asn→ ∞and the kernels are
bounded for all 0< y < x <∞, the infinite sum is indeed well defined. Now, use the
definition ofz(·), to obtain
v
g
## (x) =
λ(0)V
g
## (0)K
g,∗
## (x,0)
λ(x)
## ,(10)
whereV
g
(0) follows from normalization. The steady-state workload density is presented
in the following lemma.
Lemma 3.1.IfΛ(x)<∞for all0< x <∞, then
v
g
## (x) =
λ(0)V
g
## (0)K
g,∗
## (x,0)
λ(x)
## ,(11)
whereV
g
## (0) =
## [
## 1 +λ(0)
## ∫
## ∞
## 0
## K
g,∗
## (x,0)
λ(x)
dx
## ]
## −1
## .
In Sections 4 and 6 it is indicated how this general approach may be applied to some
(in)finite-buffer queues. Next, in Section 7, the infinite sum of Volterra kernels is explicitly
calculated for some special cases. But, we first use this Lemma to derive Equation (4).
Proof of Theorem 3.2.Observe that, by (1) and (2), the dynamics of both systems are
equivalent when
λ
## 1
## (x)
r
## 1
## (x)
## =
λ
## 2
## (x)
r
## 2
## (x)
. Hence, using a stochastic coupling argument, the first part
of the Theorem, that is (3), follows easily.
We now turn to (4). Note that Λ
## 1
## (x) = Λ
## 2
(x) implying that either the workload processes
in both systems have an atom at state zero, or not. If Λ
i
(x) =∞(i= 1,2) for some
x >0, thenV
g
i
(0) = 0 and (4) follows directly from (6) and the definition ofz(·). So,
assume thatV
g
i
(0)>0. We use the derivation of the steady-state workload density as
described above. First, observe that the kernelsK
g
(x, y) =P(g(y, B, K)> x)λ(x)/r(x)
are the same in both models, and hence, the iterated kernels and their infinite sums are
equal. Now, use (11) and dividev
g
## 1
(x) byv
g
## 2
(x) to obtain
v
g
## 1
## (x)
v
g
## 2
## (x)
## =
λ
## 1
## (0)V
g
## 1
## (0)
λ
## 2
## (0)V
g
## 2
## (0)
λ
## 2
## (x)
λ
## 1
## (x)
## ,x >0.
## Substitutingλ
## 2
## (x)/λ
## 1
## (x) =r
## 2
## (x)/r
## 1
(x) completes the proof.
## 7

Remark 3.1.There are alternative ways to solve (5). We may also divide byr(x)on
both sides of Equation (5), or definez(x) :=r(x)v
g
(x). The technique to solve the integral
equation remains the same, however, with slightly different kernels.
4  Finite-buffer dam
In this section, we study the steady-state workload distribution in the finite-buffer M/G/1
dam with general arrival rate and service speed (scenariof). The dynamics of this model
are as in Section 2, whereg(w, b, K) = min(w+b, K).  As indicated, the steady-state
workload random variables, distributions, and densities are denoted by substitutingKfor
gin Section 2, i.e.,V
## K
## , V
## K
(·), v
## K
(·) at arbitrary times andW
## K
## , W
## K
(·), w
## K
(·) just before
arrival epochs. The model with infinite buffer is denoted by just omitting thegfrom the
notation. For convenience, we refer to scenariofas the finite-buffer queue or dam in this
section.
First, we show that the steady-state workload distributions in the finite and infinite-buffer
dam are proportional. For instance, Hooghiemstra [20] based his proof for the classical
M/G/1 queue on the idea that the finite and infinite-buffer queue behave according to
similar sample paths below workload levelK. He argued that at a downcrossing of level
Kin the infinite-buffer queue, the time until the next arrival epoch is independent of
the previous arrival, and hence, the residual interarrival time behaves like an ordinary
one.  As required in the sample path comparison, we show that this lack of memory
also holds for general M/G/1-type queues with state-dependent arrival and service rates.
After making some comments about regenerative properties, the result of Hooghiemstra is
extended to our system, following similar arguments. Moreover, the steady-state workload
distribution at arrival epochs is considered.  This is no longer necessarily equal to the
workload distribution at arbitrary epochs, since the classical PASTA property no longer
holds.
Second, as an example of the general case and as a prelude to Section 5, we derive the
steady-state workload density for the finite dam, using level crossing arguments and the
Volterra successive substitution method. And third, we consider the long-run fraction of
not fully accepted customers, denoting this performance measure byP
## K
## .
The next preparatory lemma presents the lack-of-memory property of the workload decre-
ment during an interarrival interval.
Lemma 4.1.(Memoryless property). The residual workload decrement at a down-
crossing of levelxin an M/G/1 queue with arrival rateλ(·)and service rater(·)is
independent of the finished amount of work during the elapsed interarrival time, i.e.,
## P(A
x+y
> y+v|A
x+y
> y) =P(A
x
> v),x, y, v >0,   x > v
Proof.Using a simple conditioning argument and Proposition 2.1, it follows that
## P(A
x+y
> y+v|A
x+y
> y)  =e
## −
## ∫
x+y
x−v
λ(u)
r(u)
du
e
## ∫
x+y
x
λ(u)
r(u)
du
## =e
## −
## ∫
x
x−v
λ(u)
r(u)
du
## =P(A
x
> v).
Notice thatP(A
x+y
> y+v|A
x+y
> y) is independent ofy, representing the lack-of-memory
property.
## 8

Next, we state our main proportionality result.
Theorem 4.1.For0≤x≤K,
## P(V
## K
## ≤x) =
P(V≤x)
## P(V≤K)
## ,(12)
while at arrival epochs,
## P(W
## K
## ≤x) =
P(W≤x)
## P(W≤K)
## .
Before we prove the theorem, we first make some general remarks about regenerative
processes. Instead of applying level crossing arguments and using Lemma 3.1, it is also
possible to make a direct comparison between the finite and infinite-buffer queue.  We
apply the latter approach. Following Asmussen [3], we exploit the regenerative character
of the workload process and let the points with workload levelKbe its regeneration points.
Note that this is possible due to the memoryless property (Lemma 4.1). Furthermore, this
choice allows queueing systems where empty queues cannot occur. Denote the length of a
regeneration cycle in the finite and infinite-buffer queue and the number of arrivals during
this cycle, byτ
## K
,τ,N
## K
, andN, respectively. Then, the distributions ofVandV
## K
are
given by, cf. [11],
P(V≤x)  =
## 1
## Eτ
## E
## [
## ∫
τ
## 0
I(V(t)≤x)dt
## ]
## ,(13)
## P(V
## K
## ≤x)  =
## 1
## Eτ
## K
## E
## [
## ∫
τ
## K
## 0
## I(V
## K
## (t)≤x)dt
## ]
## .(14)
The distributions ofWandW
## K
can be obtained in a similar fashion, cf. [11],
P(W≤x)  =
## 1
## EN
## E
## [
## N
## ∑
i=1
## I(W
i
## ≤x)
## ]
## ,
## P(W
## K
## ≤x)  =
## 1
## EN
## K
## E
## 
## 
## N
## K
## ∑
i=1
## I(W
i
## ≤x)
## 
## 
## .
We are now ready to prove our main theorem.
Proof of Theorem 4.1.Consider the stochastic process{V(t), t≥0}.  We construct a
stochastic process
## ˆ
## V
## K
(t) directly fromV(t) and show that
## ˆ
## V
## K
(t) andV
## K
(t) are driven
by the same dynamics. First, take an arbitrary sample path ofV(t). We leave the parts
below levelKunchanged and cut out the parts of the sample path between each upcrossing
and a consecutive downcrossing of levelK. Connecting the remaining parts, we obtain
the process
## ˆ
## V
## K
(t). By the memoryless property, the workload decrement of
## ˆ
## V
## K
(t) after
hittingKbehaves like an ordinary workload decrement.  Thus
## ˆ
## V
## K
(t) andV
## K
(t) are
driven by the same dynamics and we may simplify notation by identifying the process
## {V
## K
(t), t≥0}withV
## K
## (t) :=
## ˆ
## V
## K
## (t),t≥0.
Clearly,E
## [
## ∫
τ
## 0
I(V(t)≤x)dt
## ]
andE
## [
## ∫
τ
## K
## 0
## I(V
## K
## (t)≤x)dt
## ]
are equal. Observe that
## Eτ
## K
## Eτ
represents the long-run fraction of time that the workload process of the infinite-buffer
## 9

queue is below levelKand, by (13) and (14), we have shown the first part of the theo-
rem. The second part follows directly from the same sample path construction and the
observation that
## EN
## K
## EN
equals the long-run fraction of arrivals finding the workload below
levelK. This concludes our proof.
Remark 4.1.Theorem 4.1 remains valid for any other model where the virtual waiting
time process remains unchanged below levelK(Hooghiemstra [20] noted this already for
the classical M/G/1 queue). Specifically, the theorem applies for any functiong(w, b, K),
if for allw, b, K≥0the function satisfies
g(w, b, K) =w+b,ifw+b≤K,
g(w, b, K)≥K,ifw+b > K.
## (15)
We give another example of such a system in Section 6.
In the remainder of the paper, we assume that the workload process has an atom at state
zero, i.e., Λ(x)<∞, for all 0< x <∞.
Both as an example and as a prelude to Section 5, we now further examine the steady-
state workload densityv
## K
(·). This density is well-known in case of general service rate
functions and a constant arrival rate, see e.g. [19]. A similar technique - also used in
Section 3 - may be used in case of a general arrival rate (see also [4]). We briefly indicate
how Lemma 3.1 may be used in scenariof.
We start by considering the level crossing equations,
r(x)v
## K
(x) =λ(0)V
## K
(0)(1−B(x))+
## ∫
x
## 0
## +
λ(y)v
## K
(y)(1−B(x−y))dy,0< x≤K.(16)
This equation is well-known and follows directly from an up- and downcrossing argument.
Also, (16) may be straightforwardly obtained from the general case (16) by observing that
P(g(y, B, K)> x) = 1−B(x−y) for 0≤y < x < Kand 0 otherwise. Now, it is evident
that we may define the kernel (as in [19]) byK(x, y) := (1−B(x−y))λ(x)/r(x),0≤y <
x < K. In the remainder, we refer to this kernel as the basic kernel as it appears in many
queueing systems. The iterates ofK(x, y) and the infinite sum are defined as in Section 3,
i.e., (7) and (9) respectively.
Now, applying Lemma 3.1 yields the well-known representation of the workload density
for scenariof:
v
## K
## (x) =
λ(0)V
## K
## (0)K
## ∗
## (x,0)
λ(x)
,0< x≤K,(17)
whereV
## K
(0) follows from normalization. Note that (12) can thus also be derived from the
formal solution of the density. However, we believe that the derivation of Theorem 4.1 is
especially insightful as it brings out the typical sample-path relation between the infinite
buffer queue and the finite dam (scenariof).
We conclude this section by analyzing the probability that a customer cannot be com-
pletely accepted, also referred to as loss probability. It follows directly from a regenerative
argument, see also [31], that
## P
## K
## =P(W
## K
## +B > K).
Condition onW
## K
and apply Theorem 3.1 to obtain the following corollary:
## 10

Corollary 4.1.For the loss probability in scenariof, we have
## P
## K
## =
## 1
## ̄
λ
## K
## [
λ(0)V
## K
## (0)(1−B(K)) +
## ∫
## K
## 0
## +
λ(y)v
## K
(y)(1−B(K−y))dy
## ]
## ,(18)
withv
## K
(·)given in (17) andV
## K
(0)equal to1−
## ∫
## K
## 0
v
## K
## (x)dx.
Note that other performance measures may also be directly obtained from the workload
density and Theorem 3.1.
5  First exit probabilities and cycle maxima
In this section, we focus on queues with infinite buffer capacity and determine first exit
probabilities and the distribution of the cycle maximum.  To do so, we use the finite-
buffer dam, analyzed in Section 4, to a large extent. Moreover, we show that first-exit
probabilities are related to the dual of a finite dam. Also observe that, for well-chosenK,
first-exit probabilities are the same for a range of finite-buffer models, such as the scenario
f(use Remark 4.1).
Consider the model with arrival rate 1, and release rate ˆr(x) :=
r(x)
λ(x)
when the workload
equalsx. Theorem 3.1 shows that both models have the same workload density at arrival
epochs,w(·). As a consequence, the amounts of work just after an arrival instant follow the
same distribution as well. Also, observe that the workload process{V(t), t≥0}attains
local minima just before a jump and local maxima right after a jump. Considering first-
exit probabilities, it then easily follows that we may consider (without loss of generality)
a model with arrival rate 1, and release rate ˆr(x). In fact, the same argument holds for
cycle maxima, as it may be considered to be a special case of a first-exit probability. So,
in this section we often assume, without loss of generality, that the arrival rate equals 1.
Starting with first-exit probabilities, we assume that 0≤a < b <∞, and letτ(a) :=
inf{t >0|V(t)≤a}andτ(b) := inf{t >0|V(t)≥b}correspond to the first-exit times
## 1
## .
Starting fromx, we denote the probability that the workload process hits statebbefore
stateabyU(x), i.e.,U(x) :=P
x
(τ(b)<  τ(a)).  Now, the first-exit probabilities can
be obtained from those in models with constant arrival rate (in particular [19]) and the
observation above. Define
α(a, b) :=
## [
## 1 +
r(b)
λ(b)
## ∫
b
a
λ(x)
r(x)
## K
## ∗
(b, x)dx
## ]
## −1
## .(19)
We obtain the following lemma:
Lemma 5.1.We have,
## U(x) =
## 
## 
## 
## 0,if0≤x≤a,
## ∫
x
a
u(y)dy,ifa < x≤b,
1,ifx > b,
whereu(x) =α(a, b)r(b)λ(x)K
## ∗
(b, x)/(λ(b)r(x))forx∈(a, b).
## 1
Note that we usebhere in a different fashion as in Sections 2-4. An alternative notation forbcould
beK, but we decided to follow the literature on first-exit probabilities and usebin the context of hitting
times.
## 11

Proof.Apply [19, Theorem 3] to the dam with release rate ˆr(·).
Remark 5.1.In fact, first-exit probabilities witha >0may be reduced to a similar first
exit probability witha= 0. Modify the system to a finite-buffer dam of capacityb−aand
with release rate ̆r(x) :=r(x+a)when the workload equalsx. Denote the modified first
hitting times by ̆τ(0)and ̆τ(b−a), and let, forx∈(0, b−a],
## ̆
U(x) :=P
x
## ( ̆τ(b−a)< ̆τ(0))
be the probability that the modified system hits stateb−abefore state0, starting fromx.
Then, apply Lemma 5.1 to the modified system (thus with release rate ̆r(·)). Note that
## ̆
K(x, y) = (1−B(x−y))/ ̆r(x) =K(x+a, y+a), and it can be easily shown (by induction)
that
## ̆
## K
n
(x, y) =K
n
(x+a, y+a). Now, it is just straightforward calculation to show that
## ̆
U(x−a) =U(x).
Concerning cycle maxima, we assume that at time 0 a customer enters an empty system
and defineC
max
:= sup{0≤t≤τ(0) :V(t)}. Denote  ̃r(x) := ˆr(b−x) =r(b−x) and
letP
## ̃r(·)
b
be the loss probability in a finite dam (scenariof) with release rate  ̃r(·). The
following relation between cycle maxima and loss probabilities has been obtained in [5]:
Lemma 5.2.We have,
## P(C
max
≥b) =P
## ̃r(·)
b
## .
Motivated by this relation, we first analyze scenariofwith arrival rate 1 and release rate
̃r(·) in more detail. This turns out to be a useful tool to determine the distribution of the
cycle maximum in general terms.
Let  ̃v(·) denote the steady-state workload density of the model with arrival rate 1 and
release rate  ̃r(·). Using level crossing arguments, we have, for 0< x < b,
## ̃r(x) ̃v(x) =
## ̃
V(0)(1−B(x)) +
## ∫
x
## 0
## +
̃v(y)(1−B(x−y))dy.
Definez(x) :=  ̃r(x) ̃v(x), and Volterra kernel
## ̃
K(x, y) := (1−B(x−y))/ ̃r(y), for 0< y <
x < b, and
## ̃
K(x,0) := 1−B(x) for 0< x < b. Observe that we can relate
## ̃
K(x, y) to the
basic kernel in Section 4. Specifically, for 0< y < x < b,
## ̃
K(x, y) = (1−B(b−y−(b−x)))/r(b−y) =K(b−y, b−x),
and for 0< x < b,
## ̃
K(x,0) = 1−B(b−(b−x)) =K(b, b−x)r(b).
Now, using the successive substitution method for Volterra kernels as in Section 3, yields
(for 0< x < b),
z(x)  =
## ̃
## V(0)
## ̃
## K(x,0) +
## ∫
x
## 0
## +
z(y)
## ̃
K(x, y)dy
## =
## ̃
V(0)K(b, b−x)r(b) +
## ∫
x
## 0
## +
z(y)K(b−y, b−x)dy
## =
## ̃
V(0)K(b, b−x)r(b) +
## ∫
x
## 0
## +
[K(b, b−y)K(b−y, b−x)r(b)
## ̃
## V(0)
## +
## ∫
y
## 0
K(b−u, b−y)K(b−y, b−x)z(u)du]dy
## =K
## 1
(b, b−x)r(b)
## ̃
## V(0) +K
## 2
(b, b−x)r(b)
## ̃
## V(0) +
## ∫
x
## 0
z(u)K
## 2
(b−u, b−x)du,
## 12

where the last equality follows from Fubini’s theorem and
## ∫
x
u
K(b−u, b−z)K
n
(b−z, b−x)dz=
## ∫
b−u
b−x
K(b−u, z)K
n
(z, b−x)dz
## =K
n+1
(b−u, b−x).
Iterating this argument gives
z(x) =r(b)
## ̃
## V(0)K
## ∗
(b, b−x).
Finally, use the definition ofz(·) to express the steady-state density of the model with
release rate  ̃r(·) into the original model (with release rater(·)):
## ̃v(x) =
## ̃
V(0)r(b)K
## ∗
(b, b−x)
r(b−x)
## ,(20)
where
## ̃
V(0) follows from normalization.
Returning to the cycle maximum of our original model, we have, by Lemma 5.2:
Theorem 5.1.For the cycle maximum in an M/G/1-type dam, with arrival rateλ(·)and
release rater(·), we have
## P(C
max
## ≥b) =
## ̃
V(0)(1−B(b)) +
## ∫
b
## 0
̃v(x)(1−B(b−x))dx,(21)
where
## ̃v(x) =
## ̃
V(0)r(b)K
## ∗
(b, b−x)λ(b−x)
λ(b)r(b−x)
## ,(22)
and
## ̃
## V(0) = [1 +
## ∫
b
## 0
r(b)K
## ∗
(b, b−x)λ(b−x)(λ(b)r(b−x))
## −1
dx]
## −1
## .
We give two different proofs of the above theorem; the first one uses the equivalence
between cycle maxima and loss probabilities, and the second exploits knowledge of first-
exit probabilities.
Proof I (viaP
## ̃r(·)
b
).To prove Theorem 5.1, we use the relation between loss probabilities
and cycle maxima, Lemma 5.2. We already analyzedP
r(·)
b
in Section 4 (Corollary 4.1).
Use the fact that the cycle maximum only depends onλ(·) andr(·) via their ratio and note
that the steady-state density for the model with release rate  ̃r(x) =
r(b−x)
λ(b−x)
are then given
by (20). Applying (18) to the model withλ= 1 and release rate  ̃r(·) gives the result.
Proof II (viaU(x)).First note thatα(0, b) =
## ̃
V(0), by substitutingu=b−xin (19).
Then, given the service requirement of a customer entering an empty system, the cycle
maximum may be rewritten as a first exit probability. Specifically, condition on the service
requirement of the “first customer”, and use Lemma 5.1 in the third equality:
## P(C
max
## ≥b)  =
## ∫
## ∞
x=0
U(x)dB(x)
## =
## ∫
b
x=0
## ∫
x
y=0
u(y)dydB(x) + (1−B(b))
## =
## ∫
b
y=0
α(0, b)
r(b)λ(y)K
## ∗
(b, y)
r(y)λ(b)
## ∫
b
x=y
dB(x)dy+ (1−B(b))
## =
## ∫
b
y=0
α(0, b)
r(b)λ(y)K
## ∗
(b, y)
r(y)λ(b)
(1−B(y))dy+α(0, b)(1−B(b)),
## 13

where the final step follows from (cf. (19))
1 =α(0, b) +
## ∫
b
## 0
α(0, b)
r(b)λ(y)K
## ∗
(b, y)
r(y)λ(b)
dy.
The theorem now follows by straightforward substitution.
Alternatively, the first-exit probabilities, given by Harrison and Resnick [19], may also be
related to a finite dam with release rate  ̃r(x) = ˆr(b−x) when the workload equalsx. For
a= 0 and 0≤x≤b, we use the steady-state workload density (22) directly:
## 1−
## ̃
## V(x)  =
## ∫
b
y=x
## ̃v(y)dy
## =
## ∫
b
y=x
α(0, b)
r(b)K
## ∗
(b, b−y)λ(b−y)
λ(b)r(b−y)
dy
## =
## ∫
b−x
u=0
α(0, b)
r(b)K
## ∗
(b, u)λ(u)
λ(b)r(u)
du=U(b−x),(23)
whereV(0) =α(0, b) follows from Lemma 5.1 and Theorem 5.1. Using Remark 5.1, we
may generalize this equivalence relation to cases witha >0.
Lemma 5.3.Let
## ̃
V(·)be the workload distribution of the finite-buffer system (scenariof)
of capacityb−aand release rate ̃r(·). Then, forx∈[0, b−a],
## 1−
## ̃
V(x) =U(b−x).
Proof.Consider the system with finite bufferb−aand release rate  ̃r(x) =r(b−x) when the
workload equalsx. Note that a modification of  ̃r(·) to the casea= 0 (as in Remark 5.1)
is not required, since  ̃r(x) = ˆr((b−a−x) +a).
Although the workload is upperbounded byb−a, we can use exactly the same analysis
as if it was bounded byb, and express the steady-state workload density as follows:
## ̃v(x) =
## ̃
V(0)ˆr(b)K
## ∗
(b, b−x)
## ˆr(b−x)
## ,
where
## ̃
## V(0) =
## [
## 1 +
## ∫
b−a
x=0
ˆr(b)K
## ∗
(b, b−x)
## ˆr(b−x)
dx
## ]
## −1
## ,(24)
follows from normalization. Substitutey=b−xand ˆr(x) =
r(x)
λ(x)
in (24), to see that
## ̃
## V(0) =
## [
## 1 +
## ∫
b
y=a
r(b)K
## ∗
(b, y)λ(y)
λ(b)r(y)
dy
## ]
## −1
=α(a, b).
Now, using the same argument as in (23), with substitution ˆr(y) =r(y)/λ(y) andu=b−y,
completes the proof.
Remark 5.2.We conjecture that (a modified) Lemma 5.3 also holds in case of general
i.i.d. interarrival times and a general service rater(·)if we start with a regular interarrival
interval. Denote by
## ̃
W(·)the workload distribution right before an arrival instant in the
finite-buffer system of capacityb−aand service rate ̃r(·). Then, using the machinery of
monotone stochastic recursions [1] and a similar construction as in [5], we may show that
## 1−
## ̃
W(x) =U(b−x).
## 14

6  Other finite-buffer systems
There are many finite-buffer systems, which may be distinguished by the rejection dis-
cipline of arriving customers. Among the most important ones is the finite-buffer dam
regulated by the partial rejection discipline (scenariof), see Section 4. Two other finite-
buffer systems of importance are models with customer impatience (scenarioi) and queues
governed by the complete rejection discipline (scenarioc). These models are investigated
in this section.
We begin this section by examining scenarioiand observing that for workloads less than
Kthe proportionality result (Theorem 4.1) holds. To determine the density of workloads
larger thanK, in addition to the normalizing constant, we apply level crossings and the
successive substitution method for Volterra integral equations. We conclude the study of
scenarioiby considering the loss probability. Turning to the second model, scenarioc, we
derive a formal solution for the steady-state workload density using similar techniques as
for scenarioi. Finally the loss probability in scenariocis considered.
We start with scenarioi, or equivalently, letg(w, b, K) =w+bI(w < K) in the general
set-up. Note that there existw, b, K≥0 such thatg(w, b, K)> K, implying that workload
levels aboveKmay occur. In particular, only customers arriving at the system while the
workload just before arrival is larger thanKare rejected. This resembles the impatience
of arriving customers: they are only willing to wait a maximum (stochastic) amount of
time. Moreover, as noted in [7, 20], the virtual waiting time process below levelKremains
unchanged for this model. This intuitive statement can be made rigorous by observing
that for all 0≤w≤K,g(w, b, K) =w+band thus (15) is satisfied. We consequently
have the following (see also Remark 4.1):
Corollary 6.1.For0≤x≤K, we have,
## P(V
## K,i
## ≤x) =c
## K,i
P(V≤x),(25)
withc
## K,i
some normalizing constant,P(V≤K)≤(c
## K,i
## )
## −1
≤1, while at arrival epochs of
accepted customers (thus givenW
## K,i
## ≤K),
## P(W
## K,i
≤x|W
## K,i
## ≤K) =
P(W≤x)
## P(W≤K)
## .
Remark 6.1.By a simple division and using (25) and (12) twice, we may alternatively
write, for0≤x, y≤K,
P(V≤x)
P(V≤y)
## =
## P(V
## K,i
## ≤x)
## P(V
## K,i
## ≤y)
## =
## P(V
## K
## ≤x)
## P(V
## K
## ≤y)
## .(26)
In fact, by (25), the workload distribution in the infinite-buffer case does not completely
determine the workload distribution in scenarioi. The normalizing constant can only be
determined by knowledge of the workload behavior on all possible levels of the workload
process. Forx > K, however, there seems to be no direct link to the infinite-buffer queue.
Level crossing arguments, i.e., equivalence between up- and downcrossings of a fixed level
x >0, provide a tool to resolve this issue.
Next, we derive the steady-state workload distribution for allx≥0 in scenarioi, using
the general approach described in Section 3. If the workload upon arrival is below level
K, thus 0≤w≤K, then we just haveP(g(w, B, K)>  x) = 1−B(x−w), while
## 15

P(g(w, B, K)>  w) = 0 otherwise.  The general level crossing equations can now be
rewritten into a more appealing expression: For 0< x≤K, we have
r(x)v
## K,i
(x) =λ(0)V
## K,i
(0)(1−B(x)) +
## ∫
x
## 0
## +
λ(y)v
## K,i
(y)(1−B(x−y))dy,
and forx > K,
r(x)v
## K,i
(x) =λ(0)V
## K,i
(0)(1−B(x)) +
## ∫
## K
## 0
## +
λ(y)v
## K,i
(y)(1−B(x−y))dy.(27)
The level crossing equations can be solved using Lemma 3.1, by defining the kernel
## K
i
(x, y) :=I(y < K)(1−B(x−y))λ(x)/r(x), for 0≤y < x <∞. In case 0< y≤K, we
just obtain our basic kernelK(x, y) of Section 4. By Lemma 3.1, it is thus evident that,
for 0≤x≤K,
z
## K,i
(x) =λ(0)V
## K,i
## (0)K
## ∗
## (x,0),(28)
wherez
## K,i
## (x) :=λ(x)v
## K,i
(x). The same result can be deduced from Theorem 4.1 and
## (17).
The casex > Kmay be derived in a slightly more elegant fashion; rewrite (27) into
z
## K,i
(x) =λ(0)V
## K,i
(0)K(x,0) +
## ∫
## K
## 0
## +
z
## K,i
(y)K(x, y)dy.(29)
Using the result ofz
## K,i
(y) fory≤Kand substituting this in (29), we have
z
## K,i
(x) =λ(0)V
## K,i
## (0)
## [
## K(x,0) +
## ∫
## K
## 0
K(x, y)K
## ∗
## (y,0)dy
## ]
## ,
after whichv
## K,i
## (x) =z
## K,i
(x)/λ(x) andV
## K,i
(0) can be determined by normalization.
For completeness, we give the resulting normalizing constant in general terms (takey= 0
in (26)):
c
## K,i
## =
## 1 +
## ∫
## ∞
## 0
λ(0)
λ(x)
## K
## ∗
## (x,0)dx
## 1 +
## ∫
## K
x=0
λ(0)
λ(x)
## K
## ∗
## (x,0)dx+
## ∫
## ∞
x=K
## [
λ(0)
r(x)
(1−B(x)) +
## ∫
## K
y=0
λ(0)
r(x)
(1−B(x−y))K
## ∗
## (y,0)dy
## ]
dx
## .
Remark 6.2.The cases0< x≤Kandx > Kmay be combined by writing
v
## K,i
## (x) =
λ(0)V
## K,i
## (0)
λ(x)
## [
## K(x,0) +
## ∫
x∧K
## 0
K(x, y)K
## ∗
## (y,0)dy
## ]
## .(30)
Equation (28) can then be recovered by usingK
## ∗
## (y,0) =
## ∑
## ∞
n=1
## K
n
(y,0)and interchanging
integral and sum.
Finally, it is an easy exercise to determine the long-run fraction of rejected customersP
i
## K
## .
After all, the customers that are rejected are just those that arrive while the workload is
above levelK, or more formallyP
i
## K
## =P(W
## K,i
> K). Apply Theorem 3.1 to see that
## P
i
## K
## =
## ∫
## ∞
## K
w
## K,i
## (x)dx(31)
## =
## 1
## ̄
λ
## K,i
## ∫
## ∞
## K
λ(x)v
## K,i
## (x)dx.
## 16

We now turn to scenarioc. This system is also a special case of the general set-up and can
be obtained by takingg(w, b, K) =w+bI(w+b≤K). Note that there is now∈[0, K] and
b, K≥0 such thatg(w, b, K)> K. This implies that, starting from initial workload below
K, the workload process is bounded by its buffer content and we only have to analyze
workloads belowK.
The proportionality result, as presented in Theorem 4.1, does not hold for this scenario.
Combined with Remark 4.1, this is obvious from the fact thatg(w, b, K) =w < Kfor
w∈[0, K) withw+b > K. Intuitively, the workload process below levelKis indeed
affected if a customer arrives that would cause a workload above the buffer content (in
which case that customer is completely rejected). However, we can still solve the level
crossing equations to determine the steady-state workload density.
Denote the steady-state workload density byv
## K,c
(·). Observe that an upcrossing of levelx
occurs, if at levelsy < xa customer arrives that has a service requirement larger thanx−y,
but smaller thanK−y. Specifically,P(g(y, B, K)> x) = 1−B(x−y)−(1−B(K−y)) =
B(K−y)−B(x−y). The level crossing equation may then be rewritten as follows. For
0< x < K,
r(x)v
## K,c
(x) =λ(0)V
## K,c
(0)(B(K)−B(x))+
## ∫
x
## 0
## +
λ(y)v
## K,c
(y)(B(K−y)−B(x−y))dy.(32)
In view of (8), we define the Volterra kernel asK
c
(x, y) := (B(K−y)−B(x−y))
λ(x)
r(x)
## ,
0≤y < x < K. Using Lemma 3.1 (with respective iterates and infinite sum), we can
directly write
v
## K,c
## (x) =
λ(0)V
## K,c
## (0)K
c,∗
## (x,0)
λ(x)
,0< x < K.
DeterminingV
## K,c
(0) by normalization concludes the derivation of the steady-state work-
load distribution.
Finally, we focus on the long-run fraction of rejected customers,P
c
## K
.  By definition, a
customer is rejected if, upon arrival, the workload present in addition to the service re-
quirement exceeds the buffer capacityK. Then, conditioning on the workload just before
a customer arrival and using Theorem 3.1 in the second equation, we have
## P
c
## K
## =W
## K,c
## (0)(1−B(K)) +
## ∫
## K
## 0
## +
w
## K,c
(x)(1−B(K−x))dx(33)
## =
## 1
## ̄
λ
## K,c
## [
λ(0)V
## K,c
## (0)(1−B(K)) +
## ∫
## K
## 0
## +
λ(x)v
## K,c
(x)(1−B(K−x))dx
## ]
## .
Remark 6.3.Note that the loss probabilitiesP
i
## K
andP
c
## K
only depend on the ratio between
λ(·)andr(·).  This is a direct consequence of Equations (31) and (33) in addition to
Theorem 3.2. At the intuitive level, this is evident from the fact that changing between
Models 1 and 2 (in whichλ
## 1
## (x)/r
## 1
## (x) =λ
## 2
## (x)/r
## 2
(x), for allx >0) is just a rescaling of
time. This property was obtained in [4, 28] and applied in Section 5. So, to avoid explicit
calculations of, for instance,
## ̄
λ
## K,i
and
## ̄
λ
## K,c
, we may assume (without loss of generality)
that the arrival rate is fixed.
## 17

7  Some examples
In Sections 2-6 we expressed the steady-state workload densities, first-exit probabilities,
and cycle maxima in terms of an infinite sum of Volterra kernels. Numerical methods
to compute these sums are widely available, see for example [21, 24]. Since we obtained
closed-form expressions for the performance measures of interest, we are done from a
practical point of view. However, for some special cases, the Volterra integral equations
reduce to an analytically tractable expression.
In this section, we discuss some special cases and show that several known results can be
recovered from the Volterra kernels. In addition, we derive some results that appear to be
new. We first discuss the case of constant arrival and service rate and then continue with
the case of exponential service requirements. We conclude with a remark on the extension
to rejection rules based on a stochastic barricade.
7.1  Constant arrival and service rate
Suppose thatr(x)≡r >0 andλ(x)≡λr >0. Observe that, using Theorems 3.1 and 3.2,
we may assume thatr(x)≡1 and the model thus reduces to an ordinary M/G/1 queue.
Denote the arrival rate byλ, the mean service requirement byβ, and letρ:=λβbe the
load of the system. Also, let
## H(x) :=β
## −1
## ∫
x
## 0
(1−B(y))dy,
denote the stationary residual service requirement distribution with densityh(·).
In the M/G/1 case, the basic kernelK(x, y) reduces toλ(1−B(x−y)) and it is well-known,
see for instance [19], that,
## K
## ∗
(x, y) =
## ∞
## ∑
n=1
ρ
n
h
n
## (x−y).(34)
## Here,h
n
(·) is the density of then-fold convolutionH
n
(·). Now, combine Lemma 3.1 with
(34) and take Laplace Transforms to obtain the famous Pollaczek-Khinchine formula. The
finite-dam is just the truncated version (use Theorem 4.1).
Turning to the model with customer impatience (scenarioi), the normalizing constant in
Corollary 6.1 may be determined by (26) and an application of Little’s law. First apply
(26) withy= 0:
## P(V
## K,i
≤x) =P(V≤x)
## V
## K,i
## (0)
## V(0)
## .
Then, use Little in the first and (31) and PASTA in the second equation (see also [23]),
to obtain,
## V
## K,i
(0) = 1−ρ(1−P
i
## K
) = 1−ρV
## K,i
## (K).
Apply (26) again toV
## K,i
(K) (and useV(0) = 1−ρ), then, after some rewriting, we may
express the steady-state workload density of scenarioiin terms of the classical M/G/1
queue (see also [7, 23]):
## V
## K,i
## (x) =
## V(x)
1−ρ+ρV(K)
## .
Finally, the first-exit probabilities follow from a direct computation, see [19]. Also, Tak ́acs’
formula for cycle maxima [30] may be easily recovered from Theorem 5.1 and the truncation
property for finite dams (Theorem 4.1).
## 18

7.2  Exponential service requirements
Suppose that 1−B(x) =e
## −μx
, meaning that the service requirements are exponen-
tially distributed with mean 1/μ.  For the basic kernel, we then may writeK(x, y) =
e
## −μ(x−y)
λ(x)/r(x), and we can explicitly compute (similar to [19])
## K
## ∗
(x, y) =
λ(x)
r(x)
exp{−μ(x−y) + Λ(x)−Λ(y)}.(35)
Using Lemma 3.1, the familiar steady-state workload density in the infinite-buffer queue
directly appears (see e.g. [4, 8, 19], or [3], p. 388):
v(x) =
λ(0)V(0)
r(x)
exp{−μx+ Λ(x)}.(36)
The explicit form in (35) also allows us to evaluate (30). After lengthy calculations, we
deduce the following:
Corollary 7.1.For the M/M/1 queue with customer impatience (scenarioi), arrival rate
λ(·), and service rater(·), we have
v
## K,i
## (x) =
λ(0)V
## K,i
## (0)
r(x)
exp{−μx+ Λ(x∧K)},
whereV
## K,i
(0)follows by normalization.
Turning to scenarioc(complete rejections), we obtain the following corollary:
Corollary 7.2.For the M/M/1 queue with complete rejections (scenarioc), arrival rate
λ(·), and service rater(·), we have
v
## K,c
## (x) =
## V
## K,c
## (0)λ(0)(1−e
−μ(K−x)
## )
r(x)
exp{−μx+ Λ
c
## (x)},
whereΛ
c
## (x) =
## ∫
x
## 0
λ(y)(1−e
−μ(K−y)
## )
r(y)
dyandV
## K,c
(0)follows by normalization.
Proof.Note that, by conditioning onB > x−y,P(g(y, B, K)> x) may be rewritten as
e
## −μ(x−y)
## (1−e
−μ(K−x)
). Thus, by substitution in (5), (or (32)), we have
r(x)v
g
(x) =λ(0)V
g
## (0)e
## −μx
## (1−e
−μ(K−x)
## ) +
## ∫
x
## 0
## +
λ(y)v
g
## (y)e
## −μ(x−y)
## (1−e
−μ(K−x)
## )dy.
Multiply both sides by (1−e
−μ(K−x)
## )
## −1
. Then, comparing with (16), it follows that sce-
nariocis equivalent to scenariof, but withr(x) replaced byr
c
## (x) :=r(x)(1−e
−μ(K−x)
## )
## −1
## .
Appropriately adjusting Λ(·), resulting in Λ
c
(·), and applying (36) gives the result.
The result for the classical M/M/1-queue with complete rejections [18] can now easily be
recovered from our corollary.
The first-exit probabilities may be deduced from Lemma 5.1. Alternatively, the first-exit
probabilities may also be obtained from the steady-state workload density in the finite
dam with arrival and release rateλ(b−x) andr(b−x) when the workload equalsx. The
cycle maximum can be derived in the same way.
## 19

Corollary 7.3.For the cycle maximum in an M/M/1 queue, with arrival rateλ(·)and
service rater(·), we have
## P(C
max
> x) =
## ̃
V(0) exp{Λ(x)−μx},
where
## ̃
## V(0) =
## [
## 1 +
## ∫
b
## 0
λ(x)
r(x)
exp{−μ(b−x) + Λ(b)−Λ(x)}dx
## ]
## −1
## .
Proof.Combining (22) with (35) and some rewriting yields
## ̃v(x) =
## ̃
## V(0)
λ(x)
r(x)
exp{−μx+ Λ(b)−Λ(b−x)}.
## ̃
V(0) now follows directly by normalization. Moreover, use (21),
## P(C
max
> b)  =
## ̃
## V(0)e
## −μb
## +
## ∫
b
## 0
## ̃
## V(0)e
## −μb
λ(b−x)
r(b−x)
e
Λ(b)−Λ(b−x)
dx
## =
## ̃
## V(0)e
## −μb
## [
## 1 +e
## Λ(b)
## ∫
b
## 0
λ(x)
r(x)
e
−Λ(x)
dx
## ]
## =
## ̃
## V(0)e
## −μb
## [
## 1 +e
## Λ(b)
## (
## 1−e
−Λ(b)
## )]
## =
## ̃
## V(0)e
−μb+Λ(b)
## ,
completing the proof.
7.3  Stochastic barricade
In this paper we considered an M/G/1-type model with restricted accessibility, in which
the rejection rule is based on a deterministic barricade. This may be extended by replacing
Kby a stochastic variable, see for instance [13, 28]. This extension can easily be included
into our framework. Replace at then-th arrival epochKby the random variableU
n
, with
distributionF
## U
(·) (independent of the service and arrival processes). The acceptance of
then-th customer in the scenarios of Section 2 is now determined as follows, see also [28]:
g(W
n
## , B
n
## , U
n
## ) =
## 
## 
## 
## W
n
+ min(W
n
## +B
n
## ,(U
n
## −W
n
## )
## +
## ),scenariof ,
## W
n
## +B
n
## I(W
n
## < U
n
## ),scenarioi,
## W
n
## +B
n
## I(W
n
## +B
n
## ≤U
n
## ),scenarioc.
Note that in caseλ(·) andr(·) are fixed,U
n
represents the maximal waiting time (scenario
i), or sojourn time (scenariosfandc). This model with stochastic impatience is well-
known and studied in, e.g., [13, 28].
Also in case of a random barricade, we again obtain a Volterra integral equation of the
second kind. For the given examples, we have the following Volterra kernels, where 0≤
y < x <∞(see [28]),
## K
g
(x, y) =
## 
## 
## 
## 
## 
(1−B(x−y))(1−F
## U
## (x))λ(x)/r(x),scenariof ,
(1−B(x−y))(1−F
## U
## (y))λ(x)/r(x),scenarioi,
λ(x)
r(x)
## ∫
## ∞
x
(B(z−y)−B(x−y))dF
## U
## (z),scenarioc.
Even though these kernels might be difficult to determine in general, we may express the
steady-state workload density in terms of these kernels, see Lemma 3.1. Some examples
## 20

can be found in [28] in case of exponential service requirements and either exponential or
deterministic barricades.
Finally, consider two (general) finite-buffer queues governed by the same distributions
B(·) andF
## U
(·), but with arrival and service ratesλ
i
(·) andr
i
(·),i= 1,2, such that
λ
## 1
## (x)
r
## 1
## (x)
## =
λ
## 2
## (x)
r
## 2
## (x)
, for allx >0. The queues are then related in the same way as the queues in
Section 3. From the discussion of Volterra kernels above, it is evident that (4) still holds
in this broader context. Note that the dynamics in both systems are still equal, resulting
in the generalization of (3). More general, we state that Theorems 3.1 and 3.2 also hold
in this framework.
## Acknowledgement
The author is grateful to Onno Boxma and Bert Zwart for comments on an earlier draft
of this paper and some useful remarks.
## References
[1] Asmussen, S., K. Sigman (1996). Monotone stochastic recursions and their duals.Probability in the
Engineering and Informational Sciences10, 1–20.
[2] Asmussen, S. (1998). Extreme value theory for queues via cycle maxima.Extremes2, 137–168.
[3] Asmussen, S. (2003).Applied Probability and Queues, Second Edition. Springer, New York.
[4] Bekker, R., S.C. Borst, O.J. Boxma, O. Kella (2003). Queues with workload-dependent arrival and
service rates. To appear inQueueing Systems.
[5] Bekker, R., A.P. Zwart (2003). On an equivalence between loss rates and cycle maxima in queues and
dams. SPOR-Report 2003-17, Eindhoven University of Technology.
[6] Bertrand, J.W.M., H.P.G. van Ooijen (2002). Workload based order release and productivity: a
missing link.Production Planning & Control13, 665–678.
[7] Boots, N.K., H.C. Tijms (1999). A multiserver queueing system with impatient customers.Manage-
ment Science45, 444-448.
[8] Brockwell, P.J., S.I. Resnick, R.L. Tweedie (1982). Storage processes with general release rule and
additive inputs.Advances in Applied Probability14, 392–433.
[9] Browne, S., K. Sigman (1992). Work-modulated queues with applications to storage processes.Journal
of Applied Probability29, 699–712.
[10] Cohen, J.W. (1969). Single-server queues with restricted accessibility.Journal of Engineering Math-
ematics3, 265–284.
[11] Cohen, J.W. (1976). On Regenerative Processes in Queueing Theory.Lecture Notes in Economics
and Mathematical Systems121. Springer-Verlag, Berlin.
[12] Cohen, J.W. (1982).The Single Server Queue. North-Holland Publ. Cy., Amsterdam.
[13] Daley, D.J. (1965). General customer impatience in the queueGI/G/1.Journal of Applied Probability
## 2, 186–205.
[14] Doshi, B.T. (1992). Level-crossing analysis of queues. In: Bhat, U.N., Basawa, I.V. (editors).Queueing
and Related Models. Oxford Statistical Science Series, Oxford Univ. Press, New York, 3–33.
[15] Elwalid, A., D. Mitra (1991). Analysis and design of rate-based congestion control of high-speed
networks, I: stochastic fluid models, access regulation.Queueing Systems9, 29–64.
[16] Elwalid, A., D. Mitra (1994). Statistical multiplexing with loss priorities in rate-based congestion
control of high-speed networks.IEEE Transactions on Communications42, 2989–3002.
## 21

[17] Gaver, D.P., Jr., R.G. Miller, Jr. (1962). Limiting distributions for some storage problems.Studies in
Applied Probability and Management Science(edited by K.J. Arrow, S. Karlin and H. Scarf), Stanford
## University Press, Stanford, Calif. 110–126.
[18] Gavish, B., P. Schweitzer (1977). The markovian queue with bounded waiting time.Management
## Science23, 1349–1357.
[19] Harrison, J.M., S.I. Resnick (1976). The stationary distribution and first exit probabilities of a storage
process with general release rule.Mathematics of Opererations Research1, 347–358.
[20] Hooghiemstra, G. (1987). A path construction for the virtual waiting time of an M/G/1 queue.
## Statistica Neerlandica41, 175–181.
[21] Jagerman, D. (1985). Certain Volterra integral equations arising in queueing.Stochastic Models1,
## 239–256.
[22] Kaspi, H., O. Kella, D. Perry (1996). Dam processes with state dependent batch sizes and intermittent
production processes with state dependent rates.Queueing Systems24, 37–57.
[23] Kok, A.G. de, H.C. Tijms (1985). A queueing system with impatient customers.Journal of Applied
## Probability22, 688–696.
[24] Linz, P. (1985).Analytical and Numerical Methods for Volterra Equations. SIAM Studies in Applied
Mathematics7. SIAM, Philadelphia.
[25] Loris-Teghem, J. (1972). On the waiting time distribution in a generalized queueing system with
uniformly bounded sojourn times.Journal of Applied Probability9, 642–649.
[26] Mandjes, M., D. Mitra, W.R.W. Scheinhardt (2002). A simple model of network access: feedback
adaptation of rates and admission control. In:Proceedings of Infocom 2002, 3-12.
[27] Van Ooijen, H.P.G., J.W.M. Bertrand (2003). The effects of a simple arrival rate control policy on
throughput and work-in-process in production systems with workload dependent processing rates.
International Journal of Production Economics85, 61–68.
[28] Perry, D., S. Asmussen (1995). Rejection rules in the M/G/1 queue.Queueing Systems19, 105–130.
[29] Ramanan, K., A. Weiss (1997). Sharing bandwidth in ATM. In:Proceedings of the Allerton Confer-
ence, 732–740.
[30] Tak ́acs, L. (1965). Application of Ballot theorems in the theory of queues. In: Smith, W.L., W.E.
Wilkinson (editors).Proceedings  of  the  Symposium  on  Congestion  Theory, 337–398. University of
## North Carolina Press, Chapel Hill.
[31] Zwart, A.P. (2000). A fluid queue with a finite buffer and subexponential input.Advances in Applied
## Probability32, 221–243.
[32] Zwart, A.P. (2003). Loss rates in the M/G/1 queue with complete rejection. SPOR-Report 2003-27,
Eindhoven University of Technology.
## 22