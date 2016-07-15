'''
Copyright (c) 2016, Autonomous Vehicle Systems Lab, Univeristy of Colorado at Boulder

Permission to use, copy, modify, and/or distribute this software for any
purpose with or without fee is hereby granted, provided that the above
copyright notice and this permission notice appear in all copies.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

'''
#
#   Integrated Unit Test Script
#   Purpose:  Run a test of the unit dynamics modes
#   Author:  Hanspeter Schaub
#   Creation Date:  May 22, 2016
#

import pytest
import sys, os, inspect
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
import numpy
import ctypes
import math
import csv
import logging


filename = inspect.getframeinfo(inspect.currentframe()).filename
path = os.path.dirname(os.path.abspath(filename))
splitPath = path.split('Basilisk')
sys.path.append(splitPath[0] + '/Basilisk/modules')
sys.path.append(splitPath[0] + '/Basilisk/PythonModules')

import spice_interface
import six_dof_eom
import MessagingAccess
import SimulationBaseClass
import sim_model
import unitTestSupport                  # general support file with common unit test functions
import setupUtilitiesRW                 # RW simulation setup utilties
import setupUtilitiesThruster           # Thruster simulation setup utilties
import reactionwheel_dynamics
import thruster_dynamics
import macros
import solar_panels
import fuel_tank
import vehicleConfigData







# uncomment this line is this test is to be skipped in the global unit test run, adjust message as needed
# @pytest.mark.skipif(conditionstring)
# uncomment this line if this test has an expected failure, adjust message as needed
# @pytest.mark.xfail(True)

# The following 'parametrize' function decorator provides the parameters and expected results for each
#   of the multiple test runs for this test.
@pytest.mark.parametrize("useTranslation, useRotation, useRW, useJitter, useThruster, useHingedSP, useFuelSlosh", [
    (True, True, False, False, False, False, False),
    (False, True, False, False, False, False, False),
    (True, False, False, False, False, False, False),
    (False, True, True, False, False, False, False),
    (False, True, True, True, False, False, False),
    (True, True, True, False, False, False, False),
    (True, True, True, True, False, False, False),
    (True, True, False, False, True, False, False),
    (True, True, False, False, False, True, False),
    (True, True, False, False, False, False, True),
    (True, True, False, False, False, True, True)
])

# provide a unique test method name, starting with test_
def test_unitDynamicsModes(show_plots, useTranslation, useRotation, useRW, useJitter, useThruster, useHingedSP, useFuelSlosh):
    # each test method requires a single assert method to be called
    [testResults, testMessage] = unitDynamicsModesTestFunction(
            show_plots, useTranslation, useRotation, useRW, useJitter, useThruster, useHingedSP, useFuelSlosh)
    assert testResults < 1, testMessage



def unitDynamicsModesTestFunction(show_plots, useTranslation, useRotation, useRW, useJitter, useThruster, useHingedSP, useFuelSlosh):
    testFailCount = 0                       # zero unit test result counter
    testMessages = []                       # create empty array to store test log messages
    unitTaskName = "unitTask"               # arbitrary name (don't change)
    unitProcessName = "TestProcess"         # arbitrary name (don't change)
    rwCommandName = "reactionwheel_cmds"
    thrusterCommandName = "acs_thruster_cmds"

    scSim = SimulationBaseClass.SimBaseClass()
    scSim.TotalSim.terminateSimulation()

    DynUnitTestProc = scSim.CreateNewProcess(unitProcessName)
    # create the dynamics task and specify the integration update time
    DynUnitTestProc.addTask(scSim.CreateNewTask(unitTaskName, macros.sec2nano(0.1)))
    
    VehDynObject = six_dof_eom.SixDofEOM()
    spiceObject = spice_interface.SpiceInterface()

    #Initialize the ephemeris module
    spiceObject.ModelTag = "SpiceInterfaceData"
    spiceObject.SPICEDataPath = splitPath[0] + '/Basilisk/External/EphemerisData/'
    spiceObject.UTCCalInit = "2014 March 27, 14:00:00.0"
    spiceObject.OutputBufferCount = 2
    spiceObject.PlanetNames = spice_interface.StringVector(
        ["earth"])
    spiceObject.zeroBase = "earth"
    
    mu_earth = 0.3986004415E+15 # [m^3/s^2]
    reference_radius_earth = 0.6378136300E+07 # [m]
    EarthGravBody = six_dof_eom.GravityBodyData()
    EarthGravBody.BodyMsgName = "earth_planet_data"
    EarthGravBody.outputMsgName = "earth_display_frame_data"
    EarthGravBody.IsCentralBody = True
    EarthGravBody.mu = mu_earth

    # Initialize Spacecraft Data
    VehDynObject.ModelTag = "VehicleDynamicsData"
    VehDynObject.PositionInit = six_dof_eom.DoubleVector([-4020338.690396649,	7490566.741852513,	5248299.211589362])
    VehDynObject.VelocityInit = six_dof_eom.DoubleVector([-5199.77710904224,	-3436.681645356935,	1041.576797498721])
    #Note that the above position/velocity get overwritten by the ICs from the target ephemeris
    VehDynObject.AttitudeInit = six_dof_eom.DoubleVector([0.1, 0.2, -.3])
    VehDynObject.AttRateInit = six_dof_eom.DoubleVector([0.001, -0.01, 0.03])
    VehDynObject.baseMass = 750.0
    VehDynObject.baseInertiaInit = six_dof_eom.DoubleVector([900, 0.0, 0.0,
                                                         0.0, 800.0, 0.0,
                                                         0.0, 0.0, 600.0])
    VehDynObject.baseCoMInit = six_dof_eom.DoubleVector([0.0, 0.0, 1.0])
    
    VehDynObject.AddGravityBody(EarthGravBody)
    
    VehDynObject.useTranslation = useTranslation
    VehDynObject.useRotation = useRotation

    if useThruster:
        # add thruster devices
        # The clearThrusterSetup() is critical if the script is to run multiple times
        setupUtilitiesThruster.clearThrusterSetup()
        setupUtilitiesThruster.createThruster(
                'MOOG_Monarc_1',
                [1,0,0],                # location in S frame
                [0,1,0]                 # direction in S frame
                )

        # create thruster object container and tie to spacecraft object
        thrustersDynObject = thruster_dynamics.ThrusterDynamics()
        setupUtilitiesThruster.addThrustersToSpacecraft("Thrusters",
                                                       thrustersDynObject,
                                                       VehDynObject)

        # setup the thruster mass properties
        thrusterPropCM = [0.0, 0.0, 1.2]
        thrusterPropMass = 40.0
        thrusterPropRadius = 46.0 / 2.0 / 3.2808399 / 12.0
        sphereInerita = 2.0 / 5.0 * thrusterPropMass * thrusterPropRadius * thrusterPropRadius
        thrusterPropInertia = [sphereInerita, 0, 0, 0, sphereInerita, 0, 0, 0, sphereInerita]
        thrustersDynObject.objProps.Mass = thrusterPropMass
        SimulationBaseClass.SetCArray(thrusterPropCM, 'double', thrustersDynObject.objProps.CoM)
        SimulationBaseClass.SetCArray(thrusterPropInertia, 'double', thrustersDynObject.objProps.InertiaTensor)

        # set thruster commands
        ThrustMessage = thruster_dynamics.ThrustCmdStruct()
        ThrustMessage.OnTimeRequest = 10.0
        scSim.TotalSim.CreateNewMessage(unitProcessName, thrusterCommandName, 8, 2)
        scSim.TotalSim.WriteMessageData(thrusterCommandName, 8, 0, ThrustMessage)

    if useRW:
        # add RW devices
        # The clearRWSetup() is critical if the script is to run multiple times
        setupUtilitiesRW.clearRWSetup()
        setupUtilitiesRW.options.useRWJitter = useJitter
        setupUtilitiesRW.options.maxMomentum = 100
        setupUtilitiesRW.createRW(
                'Honeywell_HR16',
                [1,0,0],                # gsHat_S
                0.0                     # RPM
                )
        setupUtilitiesRW.createRW(
                'Honeywell_HR16',
                [0,1,0],                # gsHat_S
                0.0                     # RPM
                )
        setupUtilitiesRW.createRW(
                'Honeywell_HR16',
                [0,0,1],                # gsHat_S
                0.0,                    # RPM
                [0.5,0.5,0.5]           # r_S (optional)
                )

        # create RW object container and tie to spacecraft object
        rwDynObject = reactionwheel_dynamics.ReactionWheelDynamics()
        setupUtilitiesRW.addRWToSpacecraft("ReactionWheels", rwDynObject, VehDynObject)

        # set RW torque command
        scSim.TotalSim.CreateNewMessage(unitProcessName, rwCommandName, 8*vehicleConfigData.MAX_EFF_CNT, 2)
        cmdArray = sim_model.new_doubleArray(vehicleConfigData.MAX_EFF_CNT)
        sim_model.doubleArray_setitem(cmdArray, 0, 0.020) # RW-1 [Nm]
        sim_model.doubleArray_setitem(cmdArray, 1, 0.010) # RW-2 [Nm]
        sim_model.doubleArray_setitem(cmdArray, 2,-0.050) # RW-3 [Nm]
        scSim.TotalSim.WriteMessageData(rwCommandName, 8*vehicleConfigData.MAX_EFF_CNT, 1, cmdArray )

    if useHingedSP:
        # add SPs
        VehDynObject.PositionInit = six_dof_eom.DoubleVector([0.0,	0.0, 0.0])
        VehDynObject.VelocityInit = six_dof_eom.DoubleVector([0.0,	0.0, 0.0])
        VehDynObject.AttitudeInit = six_dof_eom.DoubleVector([0.0, 0.0, 0.0])
        VehDynObject.AttRateInit = six_dof_eom.DoubleVector([0.1, -0.1, 0.1])
        panelSet1 = solar_panels.SolarPanels()
        panel1 = solar_panels.SolarPanelConfigData()
        panel2 = solar_panels.SolarPanelConfigData()

        # Define Variable for panel 1
        panel1.massSP = 100
        SimulationBaseClass.SetCArray([100.0, 0.0, 0.0, 0.0, 50, 0.0, 0.0, 0.0, 50.0], "double", panel1.ISPPntS_S)
        panel1.d = 1.5
        panel1.k = 100.0
        panel1.c = 0.0
        SimulationBaseClass.SetCArray([0.5, 0, 1], "double", panel1.r_HB_B)
        SimulationBaseClass.SetCArray([-1, 0, 0, 0, -1, 0, 0, 0, 1], "double", panel1.HB)
        panel1.theta = 5.0*numpy.pi/180
        panel1.thetaDot = 0.0

        # Define Variables for panel 2
        panel2.massSP = 100.0
        SimulationBaseClass.SetCArray([100.0, 0.0, 0.0, 0.0, 50, 0.0, 0.0, 0.0, 50.0], "double", panel2.ISPPntS_S)
        panel2.d = 1.5
        panel2.k = 100
        panel2.c = 0.0
        SimulationBaseClass.SetCArray([-0.5, 0, 1], "double", panel2.r_HB_B)
        SimulationBaseClass.SetCArray([1, 0, 0, 0, 1, 0, 0, 0, 1], "double", panel2.HB)
        panel2.theta = 0.0
        panel2.thetaDot = 0.0

        panelSet1.addSolarPanel(panel1)
        panelSet1.addSolarPanel(panel2)
        VehDynObject.addSolarPanelSet(panelSet1)

        VehDynObject.useGravity = False

    if useFuelSlosh:
        # add Fuel Slosh particles
        VehDynObject.PositionInit = six_dof_eom.DoubleVector([0.0,	0.0, 0.0])
        VehDynObject.VelocityInit = six_dof_eom.DoubleVector([0.0,	0.0, 0.0])
        VehDynObject.AttitudeInit = six_dof_eom.DoubleVector([0.0, 0.0, 0.0])
        VehDynObject.AttRateInit = six_dof_eom.DoubleVector([0.1, -0.1, 0.1])
        fuelTank1 = fuel_tank.FuelTank()
        sloshParticle1 = fuel_tank.FuelSloshParticleConfigData()
        sloshParticle2 = fuel_tank.FuelSloshParticleConfigData()
        sloshParticle3 = fuel_tank.FuelSloshParticleConfigData()

        # Define Variables for fuel tank 1
        fuelTank1.fuelTankData.massFT = 45
        SimulationBaseClass.SetCArray([0, 0, 0], "double", fuelTank1.fuelTankData.r_TB_B)

        # Define Variables for particle 1
        sloshParticle1.massFSP = 10
        sloshParticle1.k = 100.0
        sloshParticle1.c = 0.0
        SimulationBaseClass.SetCArray([0.1, 0, -0.1], "double", sloshParticle1.r_PT_B)
        SimulationBaseClass.SetCArray([1, 0, 0], "double", sloshParticle1.pHat_B)
        sloshParticle1.rho = 0.05
        sloshParticle1.rhoDot = 0.0

        # Define Variables for particle 2
        sloshParticle2.massFSP = 20
        sloshParticle2.k = 100.0
        sloshParticle2.c = 0.0
        SimulationBaseClass.SetCArray([0, 0, 0.1], "double", sloshParticle2.r_PT_B)
        SimulationBaseClass.SetCArray([0, 1, 0], "double", sloshParticle2.pHat_B)
        sloshParticle2.rho = -0.025
        sloshParticle2.rhoDot = 0.0

        # Define Variables for particle 2
        sloshParticle3.massFSP = 15
        sloshParticle3.k = 100.0
        sloshParticle3.c = 0.0
        SimulationBaseClass.SetCArray([-0.1, 0, 0.1], "double", sloshParticle3.r_PT_B)
        SimulationBaseClass.SetCArray([0, 0, 1], "double", sloshParticle3.pHat_B)
        sloshParticle3.rho = -0.015
        sloshParticle3.rhoDot = 0.0

        fuelTank1.addFuelSloshParticle(sloshParticle1)
        fuelTank1.addFuelSloshParticle(sloshParticle2)
        fuelTank1.addFuelSloshParticle(sloshParticle3)
        VehDynObject.addFuelTank(fuelTank1)

        VehDynObject.useGravity = False

    # add objects to the task process
    if useRW:
        scSim.AddModelToTask(unitTaskName, rwDynObject)
    if useThruster:
        scSim.AddModelToTask(unitTaskName, thrustersDynObject)
    scSim.AddModelToTask(unitTaskName, spiceObject)
    scSim.AddModelToTask(unitTaskName, VehDynObject)

    if useHingedSP:
        scSim.AddVariableForLogging("VehicleDynamicsData.solarPanels[0].solarPanelData[0].theta", macros.sec2nano(0.1))
        scSim.AddVariableForLogging("VehicleDynamicsData.solarPanels[0].solarPanelData[1].theta", macros.sec2nano(0.1))

    if useFuelSlosh:
        scSim.AddVariableForLogging("VehicleDynamicsData.fuelTanks[0].fuelSloshParticlesData[0].rho", macros.sec2nano(0.1))
        scSim.AddVariableForLogging("VehicleDynamicsData.fuelTanks[0].fuelSloshParticlesData[1].rho", macros.sec2nano(0.1))
        scSim.AddVariableForLogging("VehicleDynamicsData.fuelTanks[0].fuelSloshParticlesData[2].rho", macros.sec2nano(0.1))
        scSim.AddVariableForLogging("VehicleDynamicsData.totScRotKinEnergy", macros.sec2nano(0.1))
        scSim.AddVariableForLogging("VehicleDynamicsData.totScAngMomentumMag", macros.sec2nano(0.1))

    scSim.TotalSim.logThisMessage("inertial_state_output", macros.sec2nano(120.))
    
    scSim.InitializeSimulation()
    scSim.ConfigureStopTime(macros.sec2nano(60*10)) #Just a simple run to get initial conditions from ephem
    scSim.ExecuteSimulation()

    # log the data
    dataSigma = scSim.pullMessageLogData("inertial_state_output.sigma", range(3))
    dataPos = scSim.pullMessageLogData("inertial_state_output.r_N", range(3))

    if useHingedSP:
        theta1 = scSim.GetLogVariableData("VehicleDynamicsData.solarPanels[0].solarPanelData[0].theta")
        theta2 = scSim.GetLogVariableData("VehicleDynamicsData.solarPanels[0].solarPanelData[1].theta")

    if useFuelSlosh:
        rho1 = scSim.GetLogVariableData("VehicleDynamicsData.fuelTanks[0].fuelSloshParticlesData[0].rho")
        rho2 = scSim.GetLogVariableData("VehicleDynamicsData.fuelTanks[0].fuelSloshParticlesData[1].rho")
        rho3 = scSim.GetLogVariableData("VehicleDynamicsData.fuelTanks[0].fuelSloshParticlesData[2].rho")
        energy = scSim.GetLogVariableData("VehicleDynamicsData.totScRotKinEnergy")
        momentum = scSim.GetLogVariableData("VehicleDynamicsData.totScAngMomentumMag")
        # plt.figure(1)
        # plt.plot(dataPos[:,0]*1.0E-9, dataPos[:,1], 'b', dataPos[:,0]*1.0E-9, dataPos[:,2], 'g', dataPos[:,0]*1.0E-9, dataPos[:,3], 'r')
        # plt.figure(2)
        # plt.plot(dataSigma[:,0]*1.0E-9, dataSigma[:,1], 'b', dataSigma[:,0]*1.0E-9, dataSigma[:,2], 'g', dataSigma[:,0]*1.0E-9, dataSigma[:,3], 'r')
        # plt.figure(3)
        # plt.plot(rho1[:,0]*1.0E-9, rho1[:,1], 'b')
        # plt.figure(4)
        # plt.plot(rho2[:,0]*1.0E-9, rho2[:,1], 'b')
        # plt.figure(5)
        # plt.plot(rho3[:,0]*1.0E-9, rho3[:,1], 'b')
        # plt.figure(6)
        # plt.plot(theta1[:,0]*1.0E-9, theta1[:,1], 'b')
        # plt.figure(7)
        # plt.plot(theta2[:,0]*1.0E-9, theta2[:,1], 'b')
        # plt.figure(8)
        # plt.plot(energy[:,0]*1.0E-9, energy[:,1]-energy[0, 1], 'b')
        # plt.figure(9)
        # plt.plot(momentum[:,0]*1.0E-9, momentum[:,1]-momentum[0, 1], 'b')
        # plt.show()

    # set expected results
    trueSigma = [
                [ 0.0, 0.0, 0.0]
                ,[0.0, 0.0, 0.0]
                ,[0.0, 0.0, 0.0]
                ,[0.0, 0.0, 0.0]
                ,[0.0, 0.0, 0.0]
                ,[0.0, 0.0, 0.0]
                ]
    truePos = [
                [ 1.0, 0.0, 0.0]
                ,[1.0, 0.0, 0.0]
                ,[1.0, 0.0, 0.0]
                ,[1.0, 0.0, 0.0]
                ,[1.0, 0.0, 0.0]
                ,[1.0, 0.0, 0.0]
                ]
    if useTranslation==True:
        if useRotation==True and useJitter==True and useRW==True:
            truePos = [
                        [ -4.02033869e+06,   7.49056674e+06,   5.24829921e+06]
                        ,[-4.63215860e+06,   7.05702991e+06,   5.35808355e+06]
                        ,[-5.21739172e+06,   6.58298551e+06,   5.43711328e+06]
                        ,[-5.77274667e+06,   6.07124005e+06,   5.48500542e+06]
                        ,[-6.29511736e+06,   5.52480249e+06,   5.50155640e+06]
                        ,[-6.78159897e+06,   4.94686538e+06,   5.48674157e+06]
                        ]
        elif useThruster: # thrusters with no RW
            truePos = [
                        [ -4.02033869e+06,   7.49056674e+06,   5.24829921e+06]
                        ,[-4.63215747e+06,   7.05703053e+06,   5.35808358e+06]
                        ,[-5.21738942e+06,   6.58298678e+06,   5.43711335e+06]
                        ,[-5.77274323e+06,   6.07124197e+06,   5.48500554e+06]
                        ,[-6.29511282e+06,   5.52480503e+06,   5.50155656e+06]
                        ,[-6.78159336e+06,   4.94686853e+06,   5.48674175e+06]
                        ]
        elif useRotation==True and useHingedSP==True and useFuelSlosh==False: # Hinged Solar Panel Dynamics
            truePos = [
                        [0.0,                0.0,               0.0]
                        ,[-2.53742996478815, -2.84830940967875, 0.216182452815001]
                        ,[-5.38845294582063, -5.29411572920721, 0.0214874807180885]
                        ,[-7.8808739903179,  -8.17415157897987, 0.15545245637636]
                        ,[-10.5787631792684, -10.7111009304237, 0.143079770048844]
                        ,[-13.3842058040891, -13.2968874812058, 0.155873769585104]
                        ]
        elif useRotation==True and useFuelSlosh==True and useHingedSP==False: #Fuel slosh
            truePos = [
                        [0.0,              0.0,            0.0]
                        ,[-2.69102169e-02, -3.34138085e-02, -7.63296148e-03]
                        ,[-5.16421395e-02, -6.69635270e-02, -1.41925287e-02]
                        ,[-7.99673260e-02, -1.00807085e-01, -1.90481350e-02]
                        ,[-1.06932569e-01, -1.35397480e-01, -2.56727424e-02]
                        ,[-1.36388979e-01, -1.70517452e-01, -3.27473799e-02]
                        ]
        elif useRotation==True and useFuelSlosh==True and useHingedSP==True: #Fuel slosh and Hinged Dynamics
            truePos = [
                        [0.0,              0.0,            0.0]
                        ,[-2.44400224e+00, -2.74717376e+00, 2.02431956e-01]
                        ,[-5.18632064e+00, -5.11176972e+00, 1.26571309e-02]
                        ,[-7.58841749e+00, -7.88184532e+00, 1.28402447e-01]
                        ,[-1.01751925e+01, -1.03386042e+01, 1.21233539e-01]
                        ,[-1.28900259e+01, -1.28174649e+01, 1.15619983e-01]
                        ]
        else: # natural translation
            truePos = [
                        [ -4.02033869e+06,   7.49056674e+06,   5.24829921e+06]
                        ,[-4.63215860e+06,   7.05702991e+06,   5.35808355e+06]
                        ,[-5.21739172e+06,   6.58298551e+06,   5.43711328e+06]
                        ,[-5.77274669e+06,   6.07124005e+06,   5.48500543e+06]
                        ,[-6.29511743e+06,   5.52480250e+06,   5.50155642e+06]
                        ,[-6.78159911e+06,   4.94686541e+06,   5.48674159e+06]
                        ]
    if useRotation==True:
        if useRW==True:
            if useJitter==True:
                trueSigma = [
                            [1.00000000e-01,   2.00000000e-01,  -3.00000000e-01]
                            ,[-1.76673450e-01,  -4.44695362e-01,   7.55887814e-01]
                            ,[1.14010584e-01,  -3.22414666e-01,   6.83156574e-01]
                            ,[-2.24562827e-01,  -3.80868645e-01,   8.25282928e-01]
                            ,[2.17619286e-01,   2.60981727e-01,  -2.17974719e-01]
                            ,[-1.67297652e-02,  -1.74656576e-01,   4.79193617e-01]
                            ]
            else: # RW without jitter
                trueSigma = [
                            [  1.00000000e-01,   2.00000000e-01,  -3.00000000e-01]
                            ,[-1.76673530e-01,  -4.44695395e-01,   7.55888029e-01]
                            ,[ 1.12819073e-01,  -3.23001268e-01,   6.84420942e-01]
                            ,[-2.29698563e-01,  -3.85908142e-01,   8.29297402e-01]
                            ,[ 2.20123922e-01,   2.50820626e-01,  -2.08093724e-01]
                            ,[-2.37038506e-02,  -1.91520817e-01,   4.94757184e-01]
                            ]
        elif useThruster==True: # thrusters with no RW
            trueSigma = [
                        [  1.00000000e-01,  2.00000000e-01, -3.00000000e-01]
                        ,[ 1.19430832e-01,  4.59254882e-01, -3.89066833e-01]
                        ,[ 2.08138788e-01,  4.05119853e-01, -7.15382716e-01]
                        ,[-1.20724242e-01,  2.93740864e-01, -8.36793478e-01]
                        ,[ 3.07086772e-01, -5.36449617e-01,  6.59728850e-01]
                        ,[ 1.18593650e-01, -3.64833149e-01,  4.52223736e-01]
                        ]
        elif useHingedSP==True and useTranslation==True and useFuelSlosh==False: #Hinged Solar Panel Dynamics
                        trueSigma = [
                        [0.0,             0.0,            0.0]
                        ,[-0.394048228873186, -0.165364626297029, 0.169133385881799]
                        ,[0.118117327421145,  -0.0701596164151959, 0.295067094904904]
                        ,[-0.128038074707568, -0.325975851032536, -0.00401165652329442]
                        ,[-0.163301363833482, -0.366780426316819, 0.384007061361585]
                        ,[0.228198675962671, -0.329880460528557,  0.266599868549938]
                        ]
        elif useFuelSlosh==True and useTranslation==True and useHingedSP==False: #Fuel Slosh
                        trueSigma = [
                        [0.0,             0.0,            0.0]
                        ,[-8.19602045e-02, -2.38564447e-01, 8.88132824e-01]
                        ,[2.86731068e-01, -4.36081263e-02, -7.20708425e-02]
                        ,[8.62854092e-03, -6.54746392e-01, 5.93541182e-01]
                        ,[5.69042347e-01, 9.22140866e-02, -3.06825156e-02]
                        ,[-2.46306074e-01, 8.25425414e-01, -3.37112618e-01]
                        ]
        elif useFuelSlosh==True and useTranslation==True and useHingedSP==True: #Fuel Slosh and Hinged Dynamics
                        trueSigma = [
                        [0.0,             0.0,            0.0]
                        ,[-3.93694358e-01, -1.66142060e-01, 1.66953504e-01]
                        ,[1.15251028e-01, -7.13753632e-02, 2.98706088e-01]
                        ,[-1.18726297e-01, -3.23347370e-01, -2.75519994e-03]
                        ,[-1.74899479e-01, -3.73016665e-01, 3.73859155e-01]
                        ,[2.32402342e-01, -3.25845947e-01, 2.81360092e-01]
                        ]
        else: # natural dynamics without RW or thrusters
            trueSigma = [
                        [  1.00000000e-01,  2.00000000e-01, -3.00000000e-01]
                        ,[-3.38921912e-02,  -3.38798472e-01,   5.85609015e-01]
                        ,[ 2.61447681e-01,   6.34635269e-02,   4.70247303e-02]
                        ,[ 2.04899804e-01,   1.61548495e-01,  -7.03973359e-01]
                        ,[ 2.92545849e-01,  -2.01501819e-01,   3.73256986e-01]
                        ,[ 1.31464989e-01,   3.85929801e-02,  -2.48566440e-01]
                        ]

    # compare the module results to the truth values
    accuracy = 1e-9
    for i in range(0,len(trueSigma)):
        # check a vector values
        if not unitTestSupport.isArrayEqual(dataSigma[i],trueSigma[i],3,accuracy):
            testFailCount += 1
            testMessages.append("FAILED:  Dynamics Mode failed attitude unit test at t=" + str(dataSigma[i,0]*macros.NANO2SEC) + "sec\n")

    # compare the module results to the truth values
    if useHingedSP==True and useFuelSlosh==True:
        accuracy = 1e-7
    elif useHingedSP==True or useFuelSlosh==True:
        accuracy = 1e-9
    else:
        accuracy = 1e-2
    for i in range(0,len(truePos)):
        # check a vector values
        if not unitTestSupport.isArrayEqual(dataPos[i],truePos[i],3,accuracy):
            testFailCount += 1
            testMessages.append("FAILED:  Dynamics Mode failed pos unit test at t=" + str(dataPos[i,0]*macros.NANO2SEC) + "sec\n")
    
    #   print out success message if no error were found
    if testFailCount == 0:
        print   "PASSED " 

    # each test method requires a single assert method to be called
    # this check below just makes sure no sub-test failures were found
    return [testFailCount, ''.join(testMessages)]
                                                    
#
# This statement below ensures that the unit test scrip can be run as a
# stand-along python script
#
if __name__ == "__main__":
    test_unitDynamicsModes(False,       # show_plots
                           True,       # useTranslation
                           True,        # useRotation
                           False,        # useRW
                           False,        # useJitter
                           False,       # useThruster
                           False,       # useHingedSP
                           True       # useFuelSlosh
                           )
