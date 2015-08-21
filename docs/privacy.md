Private Location
================

The Mozilla Location Service is an implementation of a network
location service provider.  In plain english - that means you can take
a wifi or cellular connected device like a smart phone or desktop
computer, scan to see "what wifi routers are around me?" or "what cellular 
towers are around me?", then take those readings - upload them into
location service provider and in return - you'll get back an
approximate location for yourself.  This is 'network location' - it
typically has an accuracy of ~50m.  

Your phone can also get it's location from it's internal [GPS][1] chip 
This needs your phone to communicate with a network of satellites
which is slower, consumes much more of your battery life - but it is
also much more accurate.

If you've ever used Google Maps on your phone and seen your location
go from a big blue approximated circle down to a smaller circle -
that's your phone getting a network location and then eventually
getting the more accurate location from the GPS chip.

So network location is pretty great for most people.  

* It's fast 
* It's low power
* It's pretty accurate (usually 50m accuracy)
* It reveals your location to Google (or Apple, or Mozilla).

That last point is not so great.  In fact, it's a little terrible.

If your smartphone uses geolocation, it uses network location.  That
means that everytime you use geolocation on your phone - your location
is not only going to the application you're using, it's also going to
a third party - your location service provider.

On Android, that means Google.  For iOS, that means Apple.  For
Firefox OS - it means Mozilla gets your location.

If you consider all the applications that use geolocation you've
got on your phone, it means that the company running your location
server is getting a very good idea of your location throughout the
day.

# TODO: fill in number of times FB Messenger gets location since
# 5:15pm on Thursday June 25.

# TODO: 

So how can we do better?

Network location isn't terribly complicated.  Fundamentally, it's
looking up a bunch of wifi routers in a database and asking "Where in
the world do these routers exist in the same place?".

Getting that data onto a phone would mean that you could
disintermediate the location server.  If your phone could ask :

"Hi, I'd like to get the location database for metropolitan Toronto."

If the location server can install a small database onto your phone,
you could resolve your network location without ever revealing that
location to the server.

Concretely, if you wanted to get nearby mexican restaurants in Yelp on
your Android device, it means that Google would no longer get your
location.  Yelp still gets it, but you - the user - have already
consented to doing that.

It also means you can start doing some interesting things like offline
location.  To get 'regular' network location resolution, you require
an internet connection to ask the server "I see these 12 routers -
where am I?".  A database on your phone means that you could do the
same thing without the internet.  In cases where GPS is unusable, you 
could still get your location.

Over the last couple months, I've been working on something to do
just this.


Technical details
-----------------

My private location solution works for major city sized areas where
[Ichnaea][2] has sufficiently dense and broad collection data.

The algorithm to generate the dataset is works as follows:

1. Generate a bounding box for the city we are interested in and
extract all wifi geolocation data from Ichnaea.
2. Obtain a shapefile for the exact perimeter of the city and crop
 the 'box' of data for the city into the exact outline of the city.
3. Slice up the geography into [tiles][3].  We currently use blocks of
~150mx150m.  For metropolitan Toronto, this is equal to about 52
thousand tiles.
4. Each wifi record is now assigned into the tile that the wifi record
is contained in.

At this point, we could store the data onto disk and it would fit
inside of a couple megabytes.

We've introduced some potential privacy problems though.

The geolocation data we store in our database is actually a BSSID -
the [MAC][4] address that is unique to your wifi router.
Hypothetically, if someone obtained that address, they would be able
track the location of your router.

We mitigate this risk in a number of ways.

1. Each BSSID has it's position limited to a 150m x 150m tile, so it
we will never reveal your precise location.
2. We duplicate the your BSSID within the city boundaries
to multiple locations so that it is more difficult to resolve your
actual router location.
3. We don't even store your actual BSSID. We hash your BSSID and
truncate it so that we never leak your BSSIDs into the public.

Data duplication increases the privacy of your routers location in
exchange for an increased probability of an incorrect location fix and
volume of data that must be stored on the device.

With no obfuscation, the Toronto dataset can be stuffed inside of 3MB.
With 10x duplication of each BSSID, we get ~38MB.  At 100x, we get
380MB.  There's some room to do some clever things with disk
compression to halve those numbers, but it's pretty linear growth.
Additionally, in my own experiments, at the 100x duplication effort -
there are significant challenges around giving users an incorrect
location.


[1]: Global Positioning System "GPS"
[2]: The Mozilla Location Service http://location.services.mozilla.com "Ichnaea"
[3]: The tile size is taken from OpenStreetMaps and is equal to the
tile size at zoom level 18.
[4]: https://en.wikipedia.org/wiki/MAC_address
