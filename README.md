Ringinforequest
------

Ringinforequest Middleware for OpenStack Swift

Features
-------
 - Support Request Ringinfo  (Ringinfo APIs GET)

Install
-------

1) Install Video with ``sudo python setup.py install`` or ``sudo python
   setup.py develop`` or via whatever packaging system you may be using.

2) Alter your proxy-server.conf pipeline to have ringinforequest:

If you use keystone:

    Was::

        [pipeline:main]
        pipeline = catch_errors cache authtoken keystone proxy-server

    Change To::

        [pipeline:main]
        pipeline = catch_errors cache authtoken keystoneauth ringinforequest proxy-server

    To support Multipart Upload::

        [pipeline:main]
        pipeline = catch_errors cache swift3 s3token authtoken keystoneauth slo ringinforequest proxy-server

3) Add to your proxy-server.conf the section for the Swift3 WSGI filter::

    [filter:ringinforequest]
    use = egg:ringinforequest#ringinforequest


4) Ringinforequest config options:

 You can find a proxy config example in `gziptojson/etc/proxy-server.conf-sample`.

    # curl -X GET -I https://127.0.0.1:8080/ringinfo
