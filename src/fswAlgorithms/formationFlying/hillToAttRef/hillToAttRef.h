/*
 ISC License

 Copyright (c) 2016, Autonomous Vehicle Systems Lab, University of Colorado at Boulder

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

 */

#ifndef _HILL_TO_ATT_H
#define _HILL_TO_ATT_H

#include <vector>
#include <Eigen/Dense>
#include <stdint.h>
#include <string.h>

#include "architecture/_GeneralModuleFiles/sys_model.h"
#include "architecture/utilities/avsEigenMRP.h"
#include "architecture/utilities/bskLogging.h"
#include "architecture/messaging/messaging.h"
#include "architecture/msgPayloadDefC/AttRefMsgPayload.h"
#include "architecture/msgPayloadDefC/NavAttMsgPayload.h"
#include "architecture/msgPayloadDefC/HillRelStateMsgPayload.h"

/*! @brief Hill state to attitude reference for differential-drag control. */
class HillToAttRef: public SysModel {
public:
    HillToAttRef();
    ~HillToAttRef();
    void UpdateState(uint64_t CurrentSimNanos);
    void Reset(uint64_t CurrentSimNanos);
    AttRefMsgPayload RelativeToInertialMRP(double relativeAtt[3], double sigma_XN[3]);
    
public:
    ReadFunctor<HillRelStateMsgPayload> hillStateInMsg;
    ReadFunctor<NavAttMsgPayload> attStateInMsg;
    ReadFunctor<AttRefMsgPayload> attRefInMsg;
    Message<AttRefMsgPayload> attRefOutMsg;

    std::vector<std::vector<double>> gainMatrix; //!< Arbitrary dimension gain matrix, stored as a vector (varible length) of double,6 arrays
    BSKLogger bskLogger;                //!< -- BSK Logging
    double relMRPMax; //!< Optional maximum bound on MRP element magnitudes
    double relMRPMin; //!< Optional minimum bound on MRP element magnitudes

private:
    uint64_t OutputBufferCount;          //!< [-] Count on the number of output message buffers
};

#endif
