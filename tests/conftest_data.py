"""
tests/conftest_data.py
=======================
Large fixture data strings used by conftest.py fixtures.
"""

FULL_BIB = r"""
@book{Thrun2005ProbRobotics,
  author    = {Thrun, Sebastian and Burgard, Wolfram and Fox, Dieter},
  title     = {Probabilistic Robotics},
  publisher = {MIT Press},
  year      = {2005}
}
@article{Kalman1960,
  author  = {Kalman, R. E.},
  title   = {A New Approach to Linear Filtering and Prediction Problems},
  journal = {Transactions of the ASME},
  year    = {1960},
  volume  = {82},
  pages   = {35--45}
}
@article{Grisetti2010g2o,
  author  = {Grisetti, Giorgio and others},
  title   = {A Tutorial on Graph-Based SLAM},
  journal = {IEEE Intelligent Transportation Systems Magazine},
  year    = {2010}
}
@article{MurArtal2015ORB,
  author  = {Mur-Artal, Raul and others},
  title   = {ORB-SLAM: A Versatile and Accurate Monocular SLAM System},
  journal = {IEEE Transactions on Robotics},
  year    = {2015}
}
@article{Julier1997CovarianceIntersection,
  author  = {Julier, Simon J. and Uhlmann, Jeffrey K.},
  title   = {A Non-divergent Estimation Algorithm},
  journal = {American Control Conference},
  year    = {1997}
}
@article{GriffinBatEcholocation,
  author  = {Griffin, Donald R.},
  title   = {Listening in the Dark},
  journal = {Yale University Press},
  year    = {1958}
}
@article{GriffithBatEcholocation,
  author  = {Griffith, S. C.},
  title   = {Bat Echolocation Studies},
  journal = {Journal of Experimental Biology},
  year    = {2000}
}
@article{Simmons1979BatSonar,
  author  = {Simmons, James A.},
  title   = {Perception of Echo Phase Information in Bat Sonar},
  journal = {Science},
  year    = {1979}
}
@article{Schnitzler1968DSC,
  author  = {Schnitzler, Hans-Ulrich},
  title   = {Die Ultraschall-Ortungslaute der Hufeisen-Fledermause},
  journal = {Zeitschrift fur vergleichende Physiologie},
  year    = {1968}
}
@article{Schuller1974DSC,
  author  = {Schuller, Gerd},
  title   = {The Role of the Doppler Shift Compensation},
  journal = {Journal of Comparative Physiology},
  year    = {1974}
}
@book{MossEcholocation,
  author    = {Moss, Cynthia F. and Sinha, Shiva R.},
  title     = {Neurobiology of Echolocation in Bats},
  publisher = {Academic Press},
  year      = {2003}
}
@article{Rihaczek1969MatchedFilter,
  author  = {Rihaczek, A. W.},
  title   = {Principles of High Resolution Radar},
  journal = {McGraw-Hill},
  year    = {1969}
}
@misc{CrewAIDocs,
  title  = {CrewAI Documentation},
  url    = {https://docs.crewai.com},
  note   = {Accessed: June 2026}
}
@misc{AnthropicClaude,
  title  = {Anthropic Claude API},
  url    = {https://www.anthropic.com},
  note   = {Accessed: June 2026}
}
"""

PARTIAL_BIB = r"""
@book{Thrun2005ProbRobotics,
  author    = {Thrun, Sebastian and Burgard, Wolfram and Fox, Dieter},
  title     = {Probabilistic Robotics},
  publisher = {MIT Press},
  year      = {2005}
}
@article{Kalman1960,
  author  = {Kalman, R. E.},
  title   = {A New Approach to Linear Filtering},
  journal = {ASME Transactions},
  year    = {1960}
}
@article{Grisetti2010g2o,
  author  = {Grisetti, Giorgio},
  title   = {Graph-Based SLAM},
  journal = {IEEE ITS},
  year    = {2010}
}
@article{MurArtal2015ORB,
  author  = {Mur-Artal, Raul},
  title   = {ORB-SLAM},
  journal = {IEEE TRO},
  year    = {2015}
}
@article{Julier1997CovarianceIntersection,
  author  = {Julier, Simon},
  title   = {Covariance Intersection},
  journal = {ACC},
  year    = {1997}
}
"""
