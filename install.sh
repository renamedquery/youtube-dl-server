#!/bin/bashh
# temporary install script, will make this into a deb or something later

# qt libs
apt-get install -y qt5-default qt5-qmake libqt5sql5-mysql libqt5sql5-psql libqt5sql5-odbc libqt5sql5-sqlite libqt5core5a libqt5qml5 libqt5xml5 qtbase5-dev qtdeclarative5-dev qtbase5-dev-tools gcc g++ make cmake

# db client libs
apt-get install -y libmysqlclient-dev libpq5 libodbc1 libmongoc-dev libbson-dev