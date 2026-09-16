"""Controlled and live test suites.

These are packages so that ``tests.conftest`` resolves to one module for both pytest's
conftest loading and a test's own import. Without ``__init__.py`` the two paths produce
separate module objects, and helpers such as ``BlockedNetworkAccess`` stop comparing equal.
"""
