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
against native modules. The later native Python 3.11–3.13 matrix below also
covers the future ownership repair.

Application integration, matched pool memory measurements, and ordinary pinned
Python 3.11–3.13 builds are recorded in the downstream ypricemagic memory report.

The property and plugin 747-case comparison uses identical test source archives
and compares the original and repaired native packages. It changes 716 passes,
30 failures, and one skip into 731 passes, 15 failures, and one skip. All 13
ownership regressions and both metaclass checks pass. The same 15 pre-existing
failures remain: one create_task skip-GC assertion and 14 semaphore timing
assertions. The reports preserve each error and measured value. The full suite
is not clean. The earlier 746-case run that exposed the compiler crash remains
recorded as a failed development comparison.

## Synchronous caller interruption

A caller interruption outside `run_until_complete` could leave the created
request task pending and skip its async cleanup. The synchronous bridge now
cancels and settles its own pending task before raising the original caller
error. Cleanup failure does not replace that error. Pre-existing futures and
independent shielded requests keep their own lifetime.

A native Linux signal probe records one pending request before repair and zero
after repair, with the exact original exception preserved. Five regressions
cover custom BaseException and RuntimeError interruptions, successful and
failed cleanup, a subsequent request, and shared-request survival. The portable
tests use an owned event loop to raise caller errors outside the request task;
they do not require POSIX signals or skip Windows assertions. The real signal
probe remains separate evidence.

All five regressions fail against the original helper. All 52 focused owner
checks pass against repaired native extensions on Python 3.11, 3.12, and 3.13.
The downstream ordinary pinned matrix also passes 278 application checks and
two deadline checks per version. Four owner modules load compiled extensions,
including the synchronous helper. Owner type diagnostics remain 304 on Python
3.11 and 300 on Python 3.12/3.13. Cache and factory runtime contracts pass.

The 752-case signal-test comparison uses identical source and supporting
dependencies. It changes 745 passes, six failures, and one skip into 750 passes,
one failure, and one skip. No new failed ID appears. The create_task skip-GC
assertion remains. The previously reported 14 semaphore timing failures pass
on both sides of this later comparison; this repair does not claim to fix them.

The runtime repair is commit ed3459ee74abec91c7675f57fee4b75595edbfdc.
The portable test follow-up changes no runtime source. Downstream dependency
pins therefore retain the tested runtime commit. Exact source hashes, signal
and portable controls, native builds, type failures, and interruption evidence
are preserved in the ypricemagic sync-deadline report.

The portable 752-case comparison gives the same 745/6/1 before and 750/1/1
after counts, with identical test archives and supporting dependencies. It adds
no failed ID. These controls run on Linux ARM64. The GitHub PR has no CI runs,
so Windows execution remains unverified.
