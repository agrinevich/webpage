#!/usr/bin/perl

use strict;
use warnings;

use local::lib;
use POSIX   ();
use POSIX   qw(strftime);
use Carp    qw(carp croak);
use FindBin qw($Bin);
use File::Copy; # copy()
use Config::Tiny;
use CGI;

use lib "$Bin/../lib";
use Printer;
use Utils;

my $log = "$Bin/../logs/backup.log";
open( STDERR, '>>', $log ) or croak("Failed to append $log\n");

my $cfile = "$Bin/../main.conf";
my $conf  = Config::Tiny->read($cfile)
    or croak( "Failed to read: $cfile , " . Config::Tiny->errstr . "\n" );

my $SCRIPT     = $ENV{SCRIPT_NAME};
my $SCHEME     = $ENV{REQUEST_SCHEME};
my $HOST       = $ENV{HTTP_HOST};
my $BASE_URL   = $SCHEME . '://' . $HOST . $SCRIPT;
my $HTML_DIR   = $conf->{site}->{html_dir};
my $BACKUP_DIR = $conf->{backup}->{dir};

$CGI::POST_MAX = 1024 * 1024 * $conf->{backup}->{max_size_mb};
# $CGI::DISABLE_UPLOADS = 1;

my $q  = CGI->new();
my $do = $q->param('do') // q{};

my $p = Printer->new(
    root_dir => "$Bin/../..",
    tpl_path => '/cgi-bin/tpl',
);

my $page_left = $p->do_render(
    tpl_file => 'backup/left.html',
    escape   => 0,
    vars     => {},
);
my $page_main = q{};

if    ( $do eq 'list' )     { $page_main = list($q); }
elsif ( $do eq 'create' )   { create($q); }
elsif ( $do eq 'del' )      { del($q); }
elsif ( $do eq 'download' ) { download($q); }
elsif ( $do eq 'restore' )  { restore($q); }
elsif ( $do eq 'upload' )   { upload($q); }
else                        { $page_main = list($q); }

print $q->header(
    -type    => 'text/html',
    -charset => 'utf-8',
);

print $p->do_render(
    tpl_file => 'admin.html',
    escape   => 0,
    vars     => {
        page_left => $page_left,
        page_main => $page_main,
    },
);

close(STDERR);
exit();

sub list {
    my ($q) = @_;
    # my $msg      = $q->param('msg') // q{}; # error message
    my $list = q{};

    my ( $a_dirs, $a_files ) = Utils::read_dir( dir => $BACKUP_DIR );

    foreach my $name ( sort @{$a_files} ) {
        my $size = -s "$BACKUP_DIR/$name";

        $list .= $p->do_render(
            tpl_file => 'backup/list-file.html',
            escape   => 0,
            vars     => {
                name => $name,
                size => Utils::format_fsize($size),
            },
        );
    }

    return $p->do_render(
        tpl_file => 'backup/list.html',
        escape   => 0,
        vars     => {
            list => $list,
        },
    );
}

sub create {
    my ($q) = @_;

    my $bkp_name = strftime( '%Y%m%d-%H%M%S', localtime );
    my $bkp_dir  = $BACKUP_DIR . q{/} . $bkp_name;

    Utils::make_path( path => $bkp_dir );

    # copy html dir to bkp dir
    Utils::copy_dir(
        src_dir => $HTML_DIR,
        dst_dir => $bkp_dir,
    );

    # archive to zip
    Utils::create_zip(
        src_dir => $bkp_dir,
        dst_dir => $BACKUP_DIR,
        name    => $bkp_name,
    );

    # empty and rmdir bkp dir
    Utils::empty_dir( dir => $bkp_dir );
    rmdir($bkp_dir);

    print $q->redirect($BASE_URL);
    exit();
}

sub del {
    my ($q) = @_;

    my $filename = $q->param('name') // q{};

    my $bkp_file = $BACKUP_DIR . q{/} . $filename;
    unlink($bkp_file);

    print $q->redirect($BASE_URL);
    exit();
}

sub download {
    my ($q) = @_;

    my $filename = $q->param('name') // q{};

    my $bkp_file = $BACKUP_DIR . q{/} . $filename;

    print $q->header(
        -type       => 'application/octet-stream',
        -attachment => $filename,
    );

    binmode STDOUT;

    open( my $fh, '<', $bkp_file ) or croak($!);
    print while <$fh>;
    close($fh);

    exit();
}

sub upload {
    my ($q) = @_;

    my $filename = $q->param('file') // q{};
    if ( !$filename ) {
        print $q->redirect( $BASE_URL . '?msg=file-required' );
        exit();
    }

    my $dontup = $conf->{backup}->{dont_upload};
    my @dontup = split /[,]/, $dontup;
    my %dontup = ();
    foreach my $file_ext (@dontup) {
        $dontup{ lc $file_ext } = 1;
    }

    my @chunks = split( /[.]/, $filename );
    my $ext    = q{};
    if ( scalar @chunks > 1 ) {
        $ext = pop @chunks;
    }
    my $ext_lc = lc $ext;

    # check extension
    if ( exists $dontup{$ext_lc} ) {
        carp("Upload rejected due to disallowed file type: $ext\n");
        print $q->redirect( $BASE_URL . '?msg=rejected-file-type' );
        exit;
    }

    my $inputfh = $q->upload('file');
    if ( !$inputfh ) {
        carp("Failed to upload doc \"$filename\"\n");
        print $q->redirect( $BASE_URL . '?msg=upload-failed' );
        exit;
    }

    my $outfile = $BACKUP_DIR . '/' . $filename;
    if ( !copy( $inputfh, $outfile ) ) {
        carp("Failed to copy uploaded file to \"$outfile\": $!\n");
        print $q->redirect( $BASE_URL . '?msg=filecopy-failed' );
        exit;
    }

    print $q->redirect( $BASE_URL . '?msg=success' );
    exit();
}

sub restore {
    my ($q) = @_;

    my $filename = $q->param('name') // q{};

    my $bkp_file = $BACKUP_DIR . q{/} . $filename;

    Utils::extract_zip(
        file    => $bkp_file,
        dst_dir => $BACKUP_DIR,
    );

    # backup location now:
    my @chunks   = split /\./, $filename;
    my $ext      = pop @chunks;
    my $bkp_name = join q{.}, @chunks;
    my $bkp_dir  = $BACKUP_DIR . q{/} . $bkp_name;

    Utils::empty_dir( dir => $HTML_DIR );

    Utils::copy_dir(
        src_dir => $bkp_dir,
        dst_dir => $HTML_DIR,
    );

    Utils::empty_dir( dir => $bkp_dir );
    rmdir($bkp_dir);

    print $q->redirect( $BASE_URL . '?msg=success' );
    exit();
}

