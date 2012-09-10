function sendData() {
    function getVal() {
        return $(this).val();
    }

    var bannedTimes = $('input.banned.time').map(getVal).get();
    var bannedDays = $('input[type="checkbox"].banned.day').map(function() { return $(this).is(':checked'); }).get();
    var subCodes = $('select.subject-code').map(getVal).get();
    var nums = $('select.class-number').map(function() { return parseInt($(this).val()); }).get();
    var crns = $('input[type="checkbox"].section-pick:checked').map(function() { return parseInt($(this).attr('crn')); }).get();
    var lockCRNs = $('input[type="checkbox"].section-pick:checked').map(function() { return parseInt($(this).attr('crn')); }).get();

    $.post(
            '/solve',
            {
                'bannedTimes': JSON.stringify(bannedTimes),
                'bannedDays': JSON.stringify(bannedDays),
                'subCodes': JSON.stringify(subCodes),
                'nums': JSON.stringify(nums),
                'curCRNs': JSON.stringify(crns),
                'lockCRNs': JSON.stringify(lockCRNs)
            },
            function(clsToSections) {
                clsToSections = JSON.parse(clsToSections);

                var output = $('#output');
                output.html('');

                if ($.isEmptyObject(clsToSections)) {
                    output.html('Sorry, no schedule possible that fits the requirements.');
                } 

                for (var cls in clsToSections) {
                    output.append('<b>' + cls + '</b>');
                    var sections = clsToSections[cls];
                    for (var i = 0; i < sections.length; i++) {
                        var sec = sections[i];
                        var secDiv = $('<div class="section-out">').appendTo(output).append('- ' + sec['Type']);
                        var infoDiv = $('<div class="info-out">').appendTo(secDiv).append('CRN: ' + sec['CRN'] + '<br>' + 'Times:');
                        var timeDiv = $('<div class="time-out">').appendTo(infoDiv);
                        for (var j = 0; j < sec['Intervals'].length; j++) {
                            timeDiv.append(sec['Intervals'][j] + '<br>');
                        }
                    }
                }

                $(':button').text('Submit').attr('disabled', false);
            });
}

function checkboxHtml(cls, checked) {
    if (typeof(checked) === "undefined") {
        checked = false;
    }

    var s = '<input type="checkbox" class="' + cls + '"';
    if (checked) {
        s += ' checked';
    }
    s += '/>';
    return s;
}

$(document).ready(function() {
    var delLink = '<a href="javascript:void(0)" class="del-entry">[x]</a>';

    $('.add-ival').click(function() {
        var dayHtml = Array(6).join(checkboxHtml('day banned', true));
        var timeHtml = '<input type="text" value="08:00 AM" class="time banned"/>';

        var newDiv = $('<div>').appendTo($(this).parent()).html('<br>M/T/W/R/F' + dayHtml + timeHtml + ' to ' + timeHtml + delLink);

        newDiv.children('.time').timePicker({
            startTime: '08:00',
            endTime: '22:00',
            show24Hours: false,
            separator: ':',
            step: 10
        });

        newDiv.children('.del-entry').click(function() {
            $(this).parent().remove();
        });
    });

    $('.add-class').click(function() {
        function populateNumSel(numSel, subCode) {
            numSel.children().remove();
            var classes = subCodeToClasses[subCode];
            for (var i = 0; i < classes.length; i++) {
                numSel.append('<option>' + classes[i]['Number'] + '</option>');
            }
        }

        var _this = $(this);
        var classHtml = 'Subject: <select class="subject-code"/> Number: <select class="class-number"/>';
        var pinLink = '<a href="javascript:void(0)" class="pin-class" title="Pin a class that you\'re already in">[Pin]</a>';

        var newDiv = $('<div>').appendTo(_this.parent()).html('<br>' + classHtml + ' ' + pinLink + ' ' + delLink);

        var subCodeSel = newDiv.children('.subject-code');
        for (var i = 0; i < subCodes.length; i++) {
            subCodeSel.append('<option>' + subCodes[i] + '</option>');
        }

        var numSel = newDiv.children('.class-number');
        populateNumSel(numSel, subCodes[0]);

        subCodeSel.change(function() {
            populateNumSel(numSel, $(this).val());
        });

        function pinClassClick() {
            var _this = $(this);
            _this.text('loading...').off('click');

            subCodeSel.attr('disabled', true);
            numSel.attr('disabled', true);

            $.get(
                '/sections',
                {'subCode': subCodeSel.val(), 'num': numSel.val()},
                function(sections) {
                    var sections = JSON.parse(sections);
                    var sectionsDiv = $('<div class="sections">').appendTo(newDiv);

                    var secPickHtml = checkboxHtml('section-pick');
                    var secLockHtml = checkboxHtml('section-lock');

                    sectionsDiv.append('<p>Select the sections to pin:</p>');
                    for (var i = 0; i < sections.length; i++) {
                        var sec = sections[i];
                        var secDiv = $('<div>').appendTo(sectionsDiv).html(
                            secPickHtml + ' ' + sec['Type'] + ' | ' + sec['Section'] + ' | ' + sec['Time'] + ' | ' + sec['Days'] + '<br>'
                        );
                        secDiv.children('.section-pick').attr('crn', sec['CRN']).change(function() {
                            var _this = $(this);
                            if (_this.is(':checked')) {
                                _this.after(' <span>Lock? ' + checkboxHtml('section-lock') + '</span>');
                                _this.next('span').children('input').attr('crn', $(this).attr('crn'));
                            } else {
                                _this.next('span').remove();
                            }
                        })
                    }

                    _this.text('[Unpin]').off('click').click(function() {
                        subCodeSel.attr('disabled', false);
                        numSel.attr('disabled', false);
                        sectionsDiv.remove();

                        _this.text('[Pin]').click(pinClassClick);
                    });
                });
        }

        newDiv.children('.pin-class').click(pinClassClick);

        newDiv.children('.del-entry').click(function() {
            $(this).parent().remove();
        });
    });

    $(':button').click(function() {
        $(this).text('Loading...').attr('disabled', true);
        sendData();
    });
});
