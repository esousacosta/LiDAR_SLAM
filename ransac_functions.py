from skimage.measure import ransac, LineModelND
import threading
import numpy as np
from landmarking import *
from mainWindow import *
from PyQt5.QtCore import Qt, QPointF


THRESHOLD = 20  # maximum distance between a point and the line from the model for inlier classification
MAX_TRIALS = 100
MIN_SAMPLES = 2
MIN_POINTS = 100

#   Function to extract the line represented by the set of points for each subset of rangings. We create an x base array to be able to do << Boolean indexing >>.
def landmark_extraction(pointsToBeFitted, landmarkNumber, landmarks):
    i = 0
    equal = False
    deleteLandmark = False
    
    data = np.array(pointsToBeFitted[0][:])
    #print(data)
    del pointsToBeFitted[:]
    model_robust, inliers = ransac(data, LineModelND, min_samples=MIN_SAMPLES, 
                                   residual_threshold=THRESHOLD, max_trials=MAX_TRIALS) 
    params = model_robust.params
    a = params[1][1]/params[1][0]  # Calculating the coefficients of the line ax + b
    b = params[0][1] - a * params[0][0]
    xBase = np.array(data[inliers, 0])
    tipX = xBase[-1]  # last x point of the landmark
    tipY = tipX * a + b
    fittedLine = Landmark(a, b, landmarkNumber, params[0][0], params[0][1], tipX, tipY)  # Creation of a landmark from the previously calculated coefs.
    #  If the landmark is the same as one previously seen, we use the latter to calculate y points.
    print("ransacking...")
    if len(landmarks) > 0:# and landmarks[-1].is_equal(fittedLine):
        while i < len(landmarks) and not equal:
            equal = landmarks[i].is_equal(fittedLine)
            #  If the landmark tested is not equal to the new one it means that it has not been seen again; decrease, then, its life. If its life reaches zero, the flag deleteLandmark becomes True and it is removed from the list
            if not equal:
                deleteLandmark = landmarks[i].decrease_life()
                if deleteLandmark:
                    print("Excluded landmark: {}".format(landmarks[i]))
                    landmarks.remove(landmarks[i])
            i += 1
        if equal:  # Caso a landmark tenha sido reobservada, sua vida é recuperada
            landmarks[i - 1].reset_life()
            yBase = landmarks[i - 1].get_a() * xBase + landmarks[i - 1].get_b()#np.array(data[inliers, 1])
            newLandmark = False
        else:
            yBase = a * xBase + b  # np.array(data[inliers, 1])
            newLandmark = True
            print("New landmark found! Landmarks: {}".format(len(landmarks)))
    else:
        yBase = a * xBase + b  # np.array(data[inliers, 1])
        newLandmark = True
    qPointsList = [QPointF(xBase[i], yBase[i]) for i in range(xBase.shape[0])]
        #qPointsList.append(tempList) # Passo apenas os pontos em array para a lista final, ao invés de uma lista com um array de pointos

    #print("--------------------- Finished running RANSAC -----------------")
    return qPointsList, fittedLine, newLandmark  #yPredicted


#  Check if the code has set the flag to do the RANSAC or to clear all of the points acquired because there are less of them then the MIN_NEIGHBOORS
def check_ransac(pairInliers, tempPoints, allPoints, pointsToBeFitted, landmarks, threadEvent):#n, innerFlag):
    inliersList = list()
    #landmarks = list()
    landmarkNumber = 0
    newLandmark = True
    while True:
        if pointsToBeFitted != []:
            if pointsToBeFitted[0] != 0:
     #           print("Entrei")
     #           print(pointsToBeFitted)
                tempList, extractedLandmark, newLandmark = landmark_extraction(pointsToBeFitted, landmarkNumber, landmarks)
                inliersList.append(tempList)
                if newLandmark:
                    landmarks.append(extractedLandmark)
                    #print("Landmarks extraidas: {}".format(len(landmarks)))
                landmarkNumber += 1
            elif inliersList != []:
                #print(inliersList.copy())
                #pairInliers.put(np.concatenate(inliersList.copy(), axis=0))
                print("TROQUEEEEEEEEEEEEEEEEEEEEI\n\n\n\n\n")
                pairInliers.append(np.concatenate(inliersList.copy(), axis=0))
                allPoints.append(np.concatenate(tempPoints.copy(), axis=0))
                #a = time.time()
                #print("Passando a bola para plot\n\n\n")
                #print("Tempo:{:.8f}".format(time.time()-a))
                threadEvent.set()
                del inliersList[:]
                del pointsToBeFitted[:]
                del tempPoints[:]
            else:
                del pointsToBeFitted[:]


#   Here I run the landmark_extraction code inside an indepent process
def ransac_core(rawPoints):#, pairInliers):
    pairInliers = []
    pointsToBeFitted = []
    allPoints = []
    tempPoints = []
    landmarks = list()
    threadEvent = threading.Event()
    ransac_checking = threading.Thread(target=check_ransac, args=(pairInliers, tempPoints, allPoints, pointsToBeFitted, landmarks, threadEvent))#innerFlag))
    qt_plotting = threading.Thread(target=ploting, args=(pairInliers, allPoints, threadEvent))
    ransac_checking.start()
    qt_plotting.start()
    try:
        while True:
            time.sleep(0.000005)  # 0.00001 or 0.000001 are optimal values
            temp = rawPoints.get(True)
            pointsToBeFitted.append(temp)
            if temp != 0:
                tempPoints.append([QPointF(point[0], point[1]) for point in temp])
    except KeyboardInterrupt:
        del pointsToBeFitted
        del pairInliers
        del tempPoints
        del allPoints
        pass
