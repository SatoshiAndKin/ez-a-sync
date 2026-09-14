# Cached-property and future ownership

A shared cached-property loader retained the first instance passed to it.
The loader and a returned lambda shared one Cython closure scope. The lambda
captured the instance, and the descriptor kept the shared loader for reuse.
This could keep an otherwise unused pool or router index alive.

Both cached-property implementations now return partial(loader, instance).
The returned callable owns the instance for the pending lookup. The descriptor's
shared loader does not capture that instance.

SmartFuture and SmartTask also left a bound cleanup callback on a caller after
its await ended. That callback kept the completed future and its result alive
until the caller finished. Each await now removes that callback and its waiter
entry when it ends. The shielding callbacks use partial functions so Cython does
not create a closure cycle that retains the completed inner and outer futures.
Result transfer, exception propagation, and cancellation isolation keep their
existing behavior.

The public descriptor stub declares its inherited assignment, deletion, cache
read, and cache write methods. Assignment keeps the runtime's permitted
caller-provided cache override. Cache reads retain the descriptor's value type.
A specific async getter overload also preserves the instance and result types
when the cached-property factory receives an async function. The sync getter
contract keeps its existing behavior.

The metaclass plugin previously removed the original function from mypy's
symbol table before method analysis. It also stored unresolved signature types
in descriptor types. The additional overload exposed a compiler crash. The
plugin now preserves the original function for analysis and resolves its
signature before creating a descriptor. The existing test input now requires
resolved integer types. A new test requires both method and cached-property
body errors to be reported.

The four new property regressions cover both descriptor implementations, with
and without a setter. They check independent values, reuse, exact getter and
setter counts, and release of both the first and second instance.

Nine new future regressions cover SmartFuture, SmartTask, and shielding on
success, failure, and cancellation. They require the caller's callback count to
return to its original value while the caller still runs. Successful results
must also be released after the caller drops its handles. The tests use no
forced garbage collection or cache expiry.

All 13 new regressions fail on the original native extension. All 38 focused
property and future tests pass on the repaired Linux ARM64 Python 3.12
extensions. These include the ten existing property tests and 15 existing smart
future tests. Both controls completed within the selected Docker limits.

The static assignment/cache contract removes two diagnostics on Python 3.11,
3.12, and 3.13 without adding diagnostics. That comparison retains 304 existing
diagnostics on Python 3.11 and 300 on Python 3.12 and 3.13. A separate async
factory control removes six inference diagnostics on Python 3.12, with no added
diagnostic. Its configured check retains the same 300 existing diagnostics.
The static fixtures also execute their cache and factory value assertions
against native modules. These type checks do not imply that the final future
ownership repair has passed a native Python 3.11–3.13 matrix.

Application integration, matched pool memory measurements, and ordinary pinned
Python 3.11–3.13 builds are recorded in the downstream ypricemagic memory report.

The final 747-case full comparison uses identical test source archives and
compares the original and repaired native packages. It changes 716 passes,
30 failures, and one skip into 731 passes, 15 failures, and one skip. All 13
ownership regressions and both metaclass checks pass. The same 15 pre-existing
failures remain: one create_task skip-GC assertion and 14 semaphore timing
assertions. The reports preserve each error and measured value. The full suite
is not clean. The earlier 746-case run that exposed the compiler crash remains
recorded as a failed development comparison.
