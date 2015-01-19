# -*- encoding: utf-8 -*-
"""Test class for UI functions against an isolated capsule"""

from robottelo.test import UITestCase


class CapsuleTestCase(UITestCase):

    def capsule_errata_push(self):
        """@Test: User can push errata through to a client on
        an isolated capsule

        @Feature: Capsules

        @Setup: Client on an isolated capsule; errata synced
        on server

        @Steps:

        1. Attempt to install errata via Sat UI against client on an
        isolated capsule - this is a satellite-initiated action.

        @Assert: Errata can be installed.

        @Status: Manual

        """

    def capsule_rpm_push(self):
        """@Test: User can install a new errata on a client through
        an isolated capsule - this is a satellite-initiated action

        @Feature: Capsules

        @Setup: Client on an isolated capsule; rpms synced (RH,
        custom content)

        @Steps:

         1. attempt to push an RPM install onto client connected to
        isolated capsule - this is a satellite-initiated action.

        @Assert: Package is installed

        @Status: Manual

        """

    def capsule_puppet_push(self):
        """@test: user can install new puppet module on a client
        through an isolated capsule

        @Feature: Capsules

        @Setup: Client on an isolated capsule; puppet content synced

        @Steps:

        1. attempt to push a puppet module install initiated from
        Satellite

        @Assert: module is installed

        @Status: Manual

        """
